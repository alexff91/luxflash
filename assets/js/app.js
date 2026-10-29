/* LuxFlash main controller. Vanilla JS, no build step. */
(function () {
  "use strict";

  var WORDS = (window.LUXFLASH_WORDS || []).slice();
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var LEVELS = ["A1", "A2", "B1", "B2"];
  var ARTICLE = { m: "den", f: "d'", n: "d'" };

  /* ---------- prepare data: stable ids, indexes ---------- */
  function slug(s) {
    return String(s).toLowerCase()
      .replace(/[äàâ]/g, "a").replace(/[ëéèê]/g, "e").replace(/[ïî]/g, "i")
      .replace(/[öô]/g, "o").replace(/[üû]/g, "u").replace(/ç/g, "c")
      .replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
  }
  // Some source rows already bake the article into the headword ("d'Aarbecht",
  // "den Apel"). Strip it so we store a bare headword and add the article once,
  // consistently, at render time.
  function stripArticle(lb) {
    var s = String(lb || "");
    s = s.replace(/^d'\s*(?=\S)/i, "");               // elided: "d'Aarbecht" -> "Aarbecht"
    s = s.replace(/^(den|déi|de)\s+(?=\S)/i, "");      // spaced: "den Apel" -> "Apel"
    return s.trim();
  }
  WORDS.forEach(function (w) {
    if (w.pos === "noun") w.lb = stripArticle(w.lb);
    w.id = slug(w.lb) + "." + (w.pos || "x");
  });
  var BY_ID = {};
  WORDS.forEach(function (w) { BY_ID[w.id] = w; });

  function lodURL(word) { return "https://lod.lu/?q=" + encodeURIComponent(word); }
  function articleFor(w) {
    if (w.pos !== "noun") return "";
    var a = ARTICLE[w.gender];
    if (!a) return "";
    // the n-rule: "den" keeps its n only before a vowel and before d, t, z, n, h
    // ("den Apel", "den Dokter"); before other consonants it is "de" ("de Kéis").
    if (a === "den" && !/^[aeiouäëéèêiïöüyhndtz]/i.test(w.lb)) a = "de";
    // "d'" joins the word with no space ("d'Aarbecht"); "den"/"de" take a space
    return a + (/'$/.test(a) ? "" : " ");
  }
  function boldWord(sentence, word) {
    if (!sentence) return "";
    var esc = escapeHTML(sentence);
    var bare = String(word).split(/\s+/)[0];
    try {
      var re = new RegExp("(" + bare.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\w*)", "i");
      return esc.replace(re, "<b>$1</b>");
    } catch (e) { return esc; }
  }
  function escapeHTML(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ---------- view switching ---------- */
  $$(".tab").forEach(function (t) {
    t.addEventListener("click", function () { switchView(t.dataset.view); });
  });
  function switchView(name) {
    $$(".tab").forEach(function (t) {
      var on = t.dataset.view === name;
      t.classList.toggle("is-active", on);
      t.setAttribute("aria-selected", on ? "true" : "false");
    });
    $$(".view").forEach(function (v) { v.classList.toggle("is-active", v.id === "view-" + name); });
    if (name === "browse") renderBrowse();
    if (name === "stats") renderStats();
    if (name === "grammar") renderGrammar();
    if (name === "resources") renderResources();
    if (name === "settings") renderStorageStatus();
  }

  function renderStorageStatus() {
    var el = $("#storageStatus");
    if (!el) return;
    if (!LFStore.available) {
      el.innerHTML = "⚠️ <b>Saving is blocked in this browser</b> (private window or storage disabled). " +
        "Your progress will be lost when you close this tab — export a backup below.";
      el.style.color = "var(--again)";
      return;
    }
    var n = Object.keys(LFStore.state.cards).length;
    var txt = "✓ Autosave is on — " + n + " card" + (n === 1 ? "" : "s") + " tracked in this browser.";
    if (LFStore.persisted === true) txt += " Persistent storage granted: the browser won't evict it.";
    el.textContent = txt;
    el.style.color = "var(--good)";
  }

  /* ---------- theme ---------- */
  var themeBtn = $("#themeToggle");
  function applyTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    $(".theme-icon").textContent = t === "dark" ? "☀️" : "🌙";
  }
  (function initTheme() {
    var saved = LFStore.settings().theme;
    if (!saved) saved = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    applyTheme(saved);
  })();
  themeBtn.addEventListener("click", function () {
    var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    applyTheme(next); LFStore.setSettings({ theme: next });
  });

  /* ---------- level chips ---------- */
  var levelChips = $("#levelChips");
  function levelCount(lv) { return WORDS.filter(function (w) { return w.level === lv; }).length; }
  LEVELS.forEach(function (lv) {
    var b = document.createElement("button");
    b.className = "chip"; b.dataset.level = lv;
    b.innerHTML = lv + " <small>" + levelCount(lv) + "</small>";
    b.addEventListener("click", function () { toggleLevel(lv); });
    levelChips.appendChild(b);
  });
  function refreshChips() {
    var sel = LFStore.settings().levels;
    $$(".chip", levelChips).forEach(function (c) {
      c.classList.toggle("on", sel.indexOf(c.dataset.level) >= 0);
    });
  }
  function toggleLevel(lv) {
    var sel = LFStore.settings().levels.slice();
    var i = sel.indexOf(lv);
    if (i >= 0) {
      if (sel.length > 1) sel.splice(i, 1);
      else { toast("At least one level stays on — pick another first."); return; }
    }
    else sel.push(lv);
    LFStore.setSettings({ levels: sel });
    refreshChips(); buildSession(); nextCard();
  }

  /* ---------- session queue ---------- */
  var queue = [];
  var current = null;
  var flipped = false;
  var studyAhead = false;

  function shuffle(a) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }

  function pool() {
    var sel = LFStore.settings().levels;
    return WORDS.filter(function (w) { return sel.indexOf(w.level) >= 0; });
  }

  function buildSession() {
    var now = Date.now();
    var p = pool();
    var due = [], fresh = [];
    p.forEach(function (w) {
      var prog = LFStore.getCard(w.id);
      if (!prog) fresh.push(w);
      else if (LFsrs.isDue(prog, now)) due.push(w);
    });
    shuffle(due); shuffle(fresh);
    var limit = LFStore.settings().newPerSession;
    var list = due.concat(fresh.slice(0, limit));
    if (studyAhead && list.length === 0) {
      // nothing due: surface soonest-due / least-known cards
      list = p.slice().sort(function (a, b) {
        var pa = LFStore.getCard(a.id), pb = LFStore.getCard(b.id);
        return (pa ? pa.due : 0) - (pb ? pb.due : 0);
      }).slice(0, 30);
    }
    queue = list.map(function (w) { return w.id; });
    current = null;
  }

  function nextCard() {
    flipped = false;
    if (queue.length === 0) { current = null; render(); return; }
    current = BY_ID[queue.shift()];
    render();
  }

  /* ---------- rendering the study view ---------- */
  var elFlashcard = $("#flashcard");
  function render() {
    updateQueuePill();
    var hasCard = !!current;
    $("#studyEmpty").hidden = hasCard;
    elFlashcard.parentElement.style.display = hasCard ? "" : "none";
    $("#flipBar").style.display = hasCard ? "" : "none";
    if (!hasCard) { renderEmpty(); return; }

    var w = current;
    var reverse = LFStore.settings().reverse;
    elFlashcard.classList.remove("flipped");

    // front
    if (!reverse) {
      $("#frontPos").textContent = w.pos || "";
      $("#frontLevel").textContent = w.level || "";
      $("#frontWord").textContent = articleFor(w) + w.lb;
      $("#frontSub").textContent = w.plural ? "pl. " + w.plural : "";
      $("#frontExample").innerHTML = boldWord(w.ex_lb, w.lb);
    } else {
      $("#frontPos").textContent = w.pos || "";
      $("#frontLevel").textContent = w.level || "";
      $("#frontWord").textContent = w.en || "";
      $("#frontSub").textContent = w.de ? "🇩🇪 " + w.de : "";
      $("#frontExample").innerHTML = w.ex_en ? "<i>" + escapeHTML(w.ex_en) + "</i>" : "";
    }

    // back
    $("#backPos").textContent = w.pos || "";
    $("#lodLink").href = lodURL(w.lb);
    if (!reverse) {
      $("#backWord").textContent = w.en || "";
      $("#backTranslations").innerHTML =
        (w.de ? "<li><span class='lang'>DE</span>" + escapeHTML(w.de) + "</li>" : "") +
        (w.fr ? "<li><span class='lang'>FR</span>" + escapeHTML(w.fr) + "</li>" : "");
      $("#backExample").innerHTML = w.ex_en ? escapeHTML(w.ex_en) : "";
    } else {
      $("#backWord").textContent = articleFor(w) + w.lb;
      $("#backTranslations").innerHTML = w.plural ? "<li><span class='lang'>PL</span>" + escapeHTML(w.plural) + "</li>" : "";
      $("#backExample").innerHTML = boldWord(w.ex_lb, w.lb);
    }

    // audio: hide the front button when the front shows English (reverse mode)
    $("#frontAudio").hidden = reverse;
    preloadAudio(w);
    // auto-play when the Luxembourgish word is visible from the start
    if (!reverse && LFStore.settings().autoplay) playAudio(w, true);

    // grade hints
    var pv = LFsrs.preview(LFStore.getCard(w.id));
    $("#gtHard").textContent = pv.hard; $("#gtGood").textContent = pv.good; $("#gtEasy").textContent = pv.easy;

    showGradeBar(false);
  }

  function renderEmpty() {
    showGradeBar(false);
    var sel = LFStore.settings().levels.join(", ");
    $("#emptyMsg").textContent = studyAhead
      ? "You have studied every available card for now. Add more levels, or check back tomorrow."
      : "No cards are due in " + sel + " right now. Pick more levels above, or use “Study ahead”.";
  }

  function updateQueuePill() {
    var n = queue.length + (current ? 1 : 0);
    $("#queuePill").textContent = n + " left";
  }

  function showGradeBar(show) {
    $("#gradeBar").hidden = !show;
    $("#flipBar").style.display = show || !current ? "none" : "";
  }

  function flip() {
    if (!current) return;
    flipped = !flipped;
    elFlashcard.classList.toggle("flipped", flipped);
    showGradeBar(flipped);
    // reverse mode: the Luxembourgish answer appears on flip — auto-play it here
    if (flipped && LFStore.settings().reverse && LFStore.settings().autoplay) playAudio(current, true);
  }

  elFlashcard.addEventListener("click", flip);
  $("#flipBtn").addEventListener("click", flip);
  elFlashcard.addEventListener("keydown", function (e) {
    if (e.key === " " || e.key === "Enter") { e.preventDefault(); flip(); }
  });

  $$(".grade").forEach(function (g) {
    g.addEventListener("click", function () { gradeCurrent(g.dataset.grade); });
  });
  function gradeCurrent(grade) {
    if (!current || !flipped) return;
    var prog = LFsrs.grade(LFStore.getCard(current.id), grade);
    LFStore.setCard(current.id, prog);
    var streak = LFStore.touchStreak();
    if (grade === "again") queue.push(current.id); // re-show later this session
    nextCard();
  }

  /* ---------- practice modes ----------
     Flipping a card and saying "I knew it" is the weakest kind of recall.
     Four other ways to meet the same word, all feeding the same schedule:
       Listen - LOD's recording, pick the meaning (needs a recording);
       Type   - the meaning, type the Luxembourgish (spelling counts, an
                accent or a typo is shown and still passes);
       Gap    - LOD's own example sentence with the word blanked, pick it;
       Mix    - a different one for every word, which is what makes it stick
                (interleaving beats doing one kind of exercise in a block).
     A right answer grades "good", a wrong one "again" (back later today). */
  var MODES = ["cards", "listen", "type", "gap", "mix"];
  function mode() { var m = LFStore.settings().mode; return MODES.indexOf(m) >= 0 ? m : "cards"; }
  $$(".mode").forEach(function (b) {
    b.addEventListener("click", function () { LFStore.setSettings({ mode: b.dataset.mode }); refreshModes(); render(); });
  });
  function refreshModes() { $$(".mode").forEach(function (b) { b.classList.toggle("on", b.dataset.mode === mode()); }); }
  function bare(lb) { return String(lb).replace(/^(d'|den |de |déi )/i, ""); }
  function fold(s) { return String(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z']/g, ""); }
  function lev(a, b) {
    var m = [], i, j;
    for (i = 0; i <= a.length; i++) { m[i] = [i]; }
    for (j = 0; j <= b.length; j++) m[0][j] = j;
    for (i = 1; i <= a.length; i++) for (j = 1; j <= b.length; j++)
      m[i][j] = Math.min(m[i - 1][j] + 1, m[i][j - 1] + 1, m[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    return m[a.length][b.length];
  }
  function gapOf(w) {
    if (!w.ex_lb) return null;
    var word = bare(w.lb).split(/\s+/)[0];
    var re = new RegExp("(^|[^\\wÀ-ÿ])(" + word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")(?![\\wÀ-ÿ])", "i");
    var m = w.ex_lb.match(re);
    return m ? { before: w.ex_lb.slice(0, m.index + m[1].length), word: m[2], after: w.ex_lb.slice(m.index + m[1].length + m[2].length) } : null;
  }
  function kinds(w) {
    var k = ["type"];
    if (w.lodId) k.push("listen");
    if (gapOf(w)) k.push("gap");
    return k;
  }
  function pickKind(w) {
    var m = mode(), k = kinds(w);
    if (m !== "mix") return k.indexOf(m) >= 0 ? m : (k.indexOf("type") >= 0 ? "type" : k[0]);
    return k[Math.floor(Math.random() * k.length)];
  }
  function distractors(w, n, field) {
    var same = WORDS.filter(function (x) { return x.id !== w.id && x.pos === w.pos && x[field] && x[field] !== w[field]; });
    shuffle(same);
    var out = [], seen = {}; seen[w[field]] = 1;
    for (var i = 0; i < same.length && out.length < n; i++) if (!seen[same[i][field]]) { seen[same[i][field]] = 1; out.push(same[i]); }
    return out;
  }
  var drillBox = $("#drillBox");
  function renderDrill() {
    var w = current, kind = pickKind(w), html = "";
    drillBox.dataset.kind = kind;
    if (kind === "listen") {
      var opts = shuffle([w].concat(distractors(w, 3, "en")));
      html = '<div class="dr-q">What does it mean?</div><button class="dr-hear" id="drHear" aria-label="Listen">🔊</button>' +
        '<div class="dr-opts">' + opts.map(function (o) { return '<button class="dr-opt" data-id="' + escapeHTML(o.id) + '">' + escapeHTML(o.en) + '</button>'; }).join("") + '</div>';
    } else if (kind === "gap") {
      var g = gapOf(w), opts2 = shuffle([w].concat(distractors(w, 3, "lb")));
      html = '<div class="dr-q">Which word fits?</div><div class="dr-sent">' + escapeHTML(g.before) + '<span class="dr-blank">＿＿＿</span>' + escapeHTML(g.after) + '</div>' +
        (w.ex_en ? '<div class="dr-hint">' + escapeHTML(w.ex_en) + '</div>' : '') +
        '<div class="dr-opts">' + opts2.map(function (o) { return '<button class="dr-opt" data-id="' + escapeHTML(o.id) + '">' + escapeHTML(bare(o.lb)) + '</button>'; }).join("") + '</div>';
    } else {
      html = '<div class="dr-q">In Luxembourgish?</div><div class="dr-mean">' + escapeHTML(w.en) + '<small>' + escapeHTML(w.pos || "") + (w.de ? ' · DE ' + escapeHTML(w.de) : '') + '</small></div>' +
        '<form class="dr-type" id="drType" autocomplete="off"><input id="drIn" class="search" placeholder="type the word" autocapitalize="off" autocorrect="off" spellcheck="false" lang="lb">' +
        '<button class="btn primary" type="submit">Check</button></form>' +
        '<div class="dr-keys">' + ["ä", "ë", "é", "ö", "ü"].map(function (c) { return '<button class="dr-key" type="button">' + c + '</button>'; }).join("") + '</div>';
    }
    drillBox.innerHTML = '<div class="dr-card">' + html + '<div class="dr-fb" id="drFb"></div></div>';
    if (kind === "listen") { var hb = $("#drHear"); hb.onclick = function () { playAudio(w); }; playAudio(w, true); }
    if (kind === "type") {
      var inp = $("#drIn");
      setTimeout(function () { try { inp.focus(); } catch (e) {} }, 50);
      $$(".dr-key", drillBox).forEach(function (k) { k.onclick = function () { inp.value += k.textContent; inp.focus(); }; });
      $("#drType").onsubmit = function (e) { e.preventDefault(); answerTyped(w, inp.value); };
    }
    $$(".dr-opt", drillBox).forEach(function (b) { b.onclick = function () { answerChoice(w, b); }; });
  }
  function answerChoice(w, btn) {
    if (drillBox.dataset.done) return;
    var ok = btn.dataset.id === w.id;
    $$(".dr-opt", drillBox).forEach(function (b) { b.disabled = true; if (b.dataset.id === w.id) b.classList.add("right"); });
    if (!ok) btn.classList.add("wrong");
    finishDrill(w, ok, ok ? "" : "");
  }
  function answerTyped(w, typed) {
    if (drillBox.dataset.done) return;
    var want = bare(w.lb), t = String(typed).trim();
    var art = (t.match(/^(d'|den |de |déi )/i) || [""])[0].toLowerCase(), tw = t.slice(art.length).trim();
    var exact = tw.toLowerCase() === want.toLowerCase();
    var close = !exact && (fold(tw) === fold(want) || lev(tw.toLowerCase(), want.toLowerCase()) <= (want.length > 6 ? 2 : 1));
    var note = "";
    if (close) note = "Nearly — it is spelt <b>" + escapeHTML(want) + "</b>.";
    var wantArt = articleFor(w).trim().toLowerCase();
    if ((exact || close) && art && wantArt && art.trim() !== wantArt) note += (note ? " " : "") + "The article is <b>" + escapeHTML(articleFor(w).trim()) + "</b>.";
    finishDrill(w, exact || close, note);
  }
  function finishDrill(w, ok, note) {
    drillBox.dataset.done = "1";
    var prog = LFsrs.grade(LFStore.getCard(w.id), ok ? "good" : "again");
    LFStore.setCard(w.id, prog); LFStore.touchStreak();
    if (!ok) queue.push(w.id);
    $("#drFb").innerHTML = '<div class="dr-res ' + (ok ? "ok" : "no") + '">' + (ok ? "✓ Right" : "✗ Not this time — it comes back later today") + '</div>' +
      (note ? '<div class="dr-note">' + note + '</div>' : '') +
      '<div class="dr-answer"><b>' + escapeHTML(articleFor(w) + w.lb) + '</b> — ' + escapeHTML(w.en || "") + (w.lodId ? ' <button class="dr-say" id="drSay" aria-label="Listen">🔊</button>' : '') + '</div>' +
      (w.ex_lb ? '<div class="dr-ex">' + boldWord(w.ex_lb, w.lb) + (w.ex_en ? '<small>' + escapeHTML(w.ex_en) + '</small>' : '') + '</div>' : '') +
      '<button class="btn primary big" id="drNext">Next</button>';
    var say = $("#drSay"); if (say) say.onclick = function () { playAudio(w); };
    if (w.lodId && drillBox.dataset.kind !== "listen") playAudio(w, true);
    $("#drNext").onclick = function () { nextCard(); };
    try { $("#drNext").focus(); } catch (e) {}
  }
  var baseRender = render;
  render = function () {
    var drill = mode() !== "cards" && !!current;
    drillBox.hidden = !drill;
    delete drillBox.dataset.done;
    if (!drill) { elFlashcard.parentElement.style.display = ""; return baseRender(); }
    updateQueuePill();
    $("#studyEmpty").hidden = true;
    elFlashcard.parentElement.style.display = "none";
    $("#flipBar").style.display = "none";
    showGradeBar(false); $("#flipBar").style.display = "none";
    renderDrill();
  };
  refreshModes();
  // for the end-to-end check of the practice modes (scripts' Playwright run)
  window.LFDebug = { current: function () { return current; }, article: articleFor };

  /* keyboard shortcuts */
  document.addEventListener("keydown", function (e) {
    if (/^(input|textarea|select)$/i.test(e.target.tagName)) return;
    if (!$("#view-study").classList.contains("is-active")) return;
    if (mode() !== "cards") { if (e.key === "Enter" && $("#drNext")) { e.preventDefault(); $("#drNext").click(); } return; }
    if (e.key === " ") { e.preventDefault(); flip(); return; }
    if (e.key === "p" || e.key === "P") { if (current) playAudio(current); return; }
    if (flipped) {
      if (e.key === "1") gradeCurrent("again");
      else if (e.key === "2") gradeCurrent("hard");
      else if (e.key === "3") gradeCurrent("good");
      else if (e.key === "4") gradeCurrent("easy");
    }
  });

  $("#reverseMode").addEventListener("change", function (e) {
    LFStore.setSettings({ reverse: e.target.checked }); render();
  });
  $("#autoPlay").addEventListener("change", function (e) {
    LFStore.setSettings({ autoplay: e.target.checked });
  });
  $("#studyAnywayBtn").addEventListener("click", function () {
    studyAhead = true; buildSession(); nextCard();
  });

  /* ---------- audio ----------
     Prefer the real LOD recording when a word has a `lodId` (LOD hosts
     pronunciation openly / CC0 at https://lod.lu/uploads/OGG/<id>.ogg and
     /AAC/<id>.m4a — populate ids via scripts/fetch_lod_audio.py). Otherwise
     fall back to browser speech: no browser ships a Luxembourgish voice yet,
     so prefer an lb voice if one ever exists, then German (closest phonetics)
     rather than defaulting to an English voice. */
  function pickVoice() {
    var voices = window.speechSynthesis.getVoices() || [];
    return voices.find(function (v) { return /^lb\b/i.test(v.lang); })
        || voices.find(function (v) { return /^de\b/i.test(v.lang); })
        || null;
  }
  function speakWord(text) {
    if (!text || !window.speechSynthesis) return;
    var go = function () {
      var u = new SpeechSynthesisUtterance(text);
      var v = pickVoice();
      if (v) { u.voice = v; u.lang = v.lang; } else { u.lang = "de-DE"; }
      u.rate = 0.9;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    };
    // getVoices() is often empty until the voiceschanged event fires
    if ((window.speechSynthesis.getVoices() || []).length) go();
    else window.speechSynthesis.addEventListener("voiceschanged", go, { once: true });
  }
  // Safari (every iPhone) cannot play Ogg Vorbis: there the first tap used to
  // fail and fall back to a German browser voice. Ask the browser first, the
  // way the path and drill pages already did.
  var CAN_OGG = !!(document.createElement("audio").canPlayType || function () { return ""; }).call(document.createElement("audio"), 'audio/ogg; codecs="vorbis"');
  function lodAudioURLs(id) {
    id = String(id).toLowerCase();
    var ogg = "https://lod.lu/uploads/OGG/" + id + ".ogg", aac = "https://lod.lu/uploads/AAC/" + id + ".m4a";
    return CAN_OGG ? [ogg, aac] : [aac, ogg];
  }

  // Keep a tiny cache of preloaded Audio elements so the 🔊 tap is instant.
  var audioCache = {};
  var audioCacheOrder = [];
  function preloadAudio(word) {
    if (!word || !word.lodId || audioCache[word.lodId]) return;
    var a = new Audio();
    a.preload = "auto";
    a.src = lodAudioURLs(word.lodId)[0];
    audioCache[word.lodId] = a;
    audioCacheOrder.push(word.lodId);
    if (audioCacheOrder.length > 20) delete audioCache[audioCacheOrder.shift()];
  }

  function markPlaying(on) {
    $$(".face-audio").forEach(function (b) { b.classList.toggle("playing", on); });
  }
  function playAudio(word, quiet) {
    if (!word) return;
    if (word.lodId) {
      var urls = lodAudioURLs(word.lodId), i = 0;
      var a = audioCache[word.lodId] || new Audio();
      if (!a.src) a.src = urls[0];
      var fallback = function () {
        i++;
        if (i < urls.length) { a = new Audio(); a.src = urls[i]; hook(a); a.play().catch(done); }
        else if (!quiet) speakWord(word.lb);
      };
      var done = function () { markPlaying(false); };
      var hook = function (el) {
        el.onerror = fallback;
        el.onended = done; el.onpause = done;
      };
      hook(a);
      a.currentTime = 0;
      markPlaying(true);
      a.play().then(null, function () { markPlaying(false); if (!quiet) speakWord(word.lb); });
      return;
    }
    if (!quiet) speakWord(word.lb);
  }
  ["speakBtn", "frontAudio", "backAudio"].forEach(function (id) {
    var el = $("#" + id);
    if (!el) return;
    el.addEventListener("click", function (e) {
      e.stopPropagation();
      if (current) playAudio(current);
    });
  });

  /* ---------- grammar ---------- */
  function renderGrammar() {
    var host = $("#grammarList");
    if (host.dataset.done) return;
    var G = window.LUXFLASH_GRAMMAR || [];
    host.innerHTML = G.map(function (sec, idx) {
      return '<details class="gram-item"' + (idx === 0 ? " open" : "") + '>' +
        '<summary>' + escapeHTML(sec.title) + '</summary>' +
        '<div class="gram-body">' +
        (sec.intro ? '<p>' + escapeHTML(sec.intro) + '</p>' : '') +
        (sec.body || []).map(renderGrammarBlock).join("") +
        '</div></details>';
    }).join("");
    host.dataset.done = "1";
  }
  function renderGrammarBlock(b) {
    if (b.type === "p") return '<p>' + b.text + '</p>';
    if (b.type === "list") return '<ul class="gram-ul">' + b.items.map(function (i) { return '<li>' + i + '</li>'; }).join("") + '</ul>';
    if (b.type === "ex") return '<div class="gram-ex"><span class="gex-lb">' + escapeHTML(b.lb) + '</span><span class="gex-en">' + escapeHTML(b.en) + '</span></div>';
    if (b.type === "tip") return '<div class="gram-tip">💡 ' + escapeHTML(b.text) + '</div>';
    if (b.type === "table") return '<div class="gram-table-wrap"><table class="gram-table"><thead><tr>' +
      b.head.map(function (h) { return '<th>' + escapeHTML(h) + '</th>'; }).join("") + '</tr></thead><tbody>' +
      b.rows.map(function (r) { return '<tr>' + r.map(function (c) { return '<td>' + escapeHTML(c) + '</td>'; }).join("") + '</tr>'; }).join("") +
      '</tbody></table></div>';
    return "";
  }

  /* ---------- resources ---------- */
  var RESOURCES = [
    { name: "Luxembourgish with Anne", url: "https://luxembourgishwithanne.lu/", tag: "Courses · Blog · Podcast",
      desc: "The best-known Luxembourgish teacher online. Self-study A1–B courses, a free sentence-structure mini-course, flashcards, and Sproochentest exam prep." },
    { name: "LOD — Lëtzebuerger Online Dictionnaire", url: "https://lod.lu/", tag: "Official dictionary",
      desc: "The official dictionary: meanings, native audio, IPA, examples and full declensions. Every LuxFlash card links here. Data is open (CC0)." },
    { name: "Luxembourgish with Anne — Podcast", url: "https://open.spotify.com/show/00VXbMpd9bHNxc4p08qDjl", tag: "Listening",
      desc: "Short episodes to train your ear, also on Apple Podcasts and YouTube." },
    { name: "Zentrum fir d'Lëtzebuerger Sprooch (ZLS)", url: "https://portal.education.lu/zls/", tag: "Language authority",
      desc: "The official body for Luxembourgish: orthography rules, the Sproochenhaus, and reference resources." },
    { name: "LOD open data & API", url: "https://data.public.lu/en/datasets/letzebuerger-online-dictionnaire-lod-public-api/", tag: "Developers",
      desc: "The full LOD dataset and a public REST API, including the open audio files used for native pronunciation." },
    { name: "RTL Lëtzebuerg", url: "https://www.rtl.lu/", tag: "Authentic input",
      desc: "News, radio and TV in Luxembourgish — real-world listening and reading once you reach A2/B1." },
    { name: "lod-anki (open source)", url: "https://github.com/brunopacheco1/lod-anki", tag: "Anki decks",
      desc: "Community project that turns LOD content (with audio) into Anki flashcards — handy if you also use Anki." },
    { name: "Sproochentest — naturalisation test", url: "https://guichet.public.lu/en/citoyens/citoyennete/nationalite-luxembourgeoise/acquisition-recouvrement/conditions-prealables.html", tag: "Exam",
      desc: "Official conditions for citizenship on guichet.lu: the Sproochentest (A2 speaking, B1 listening), the fee and how to register with the INL." },
    { name: "Generalprouf — rehearse the oral test", url: "https://generalprouf.alftech.space/", tag: "Speaking",
      desc: "A dress rehearsal for the Sproochentest: the examiner asks in Luxembourgish, you answer out loud and hear yourself back. Thirty days, a picture part and mock exams." },
    { name: "LLO.lu — Lëtzebuergesch Léieren Online", url: "https://www.llo.lu/", tag: "Free official courses",
      desc: "The government's free e-learning platform (by the INL): full CEFR-structured courses A1–B2 with audio, speech-recognition exercises and live conversation tables." },
    { name: "INL — Institut National des Langues", url: "https://www.inll.lu/", tag: "Classes & exams",
      desc: "Luxembourg's national language institute: in-person and online Luxembourgish classes, plus the official language certifications." },
    { name: "Spellchecker.lu", url: "https://spellchecker.lu/", tag: "Writing tool",
      desc: "Free Luxembourgish spelling and grammar checker — paste any text and correct it; also ships browser add-ons and office plugins." },
    { name: "Radio 100,7", url: "https://www.100komma7.lu/", tag: "Listening",
      desc: "Luxembourg's public radio, entirely in Luxembourgish — clear, calm speech that's great listening practice from B1." },
    { name: "Lëtzebuergesch Wikipedia", url: "https://lb.wikipedia.org/", tag: "Reading",
      desc: "Thousands of articles written in Luxembourgish — pick a topic you know well and read it in Lëtzebuergesch." },
    { name: "Learn Luxembourgish (Liz Wenger)", url: "https://learnluxembourgish.com/", tag: "Courses · Vocabulary",
      desc: "Online courses, vocabulary lists and learning tips from a certified Luxembourgish teacher." }
  ];
  function renderResources() {
    var host = $("#resGrid");
    if (host.dataset.done) return;
    host.innerHTML = RESOURCES.map(function (r) {
      return '<a class="res-card" href="' + r.url + '" target="_blank" rel="noopener">' +
        '<div class="res-top"><span class="res-name">' + escapeHTML(r.name) + '</span><span class="res-go">↗</span></div>' +
        '<span class="res-tag">' + escapeHTML(r.tag) + '</span>' +
        '<p class="res-desc">' + escapeHTML(r.desc) + '</p></a>';
    }).join("");
    host.dataset.done = "1";
  }

  /* ---------- browse ---------- */
  var catFilter = $("#catFilter");
  (function fillCats() {
    var cats = {};
    WORDS.forEach(function (w) { if (w.category) cats[w.category] = (cats[w.category] || 0) + 1; });
    var opt = document.createElement("option"); opt.value = ""; opt.textContent = "All categories";
    catFilter.appendChild(opt);
    Object.keys(cats).sort().forEach(function (c) {
      var o = document.createElement("option"); o.value = c; o.textContent = c + " (" + cats[c] + ")";
      catFilter.appendChild(o);
    });
  })();
  var searchInput = $("#searchInput");
  var debounceT = null;
  [searchInput].forEach(function (el) { el.addEventListener("input", function () { clearTimeout(debounceT); debounceT = setTimeout(renderBrowse, 120); }); });
  catFilter.addEventListener("change", renderBrowse);
  $("#levelFilter").addEventListener("change", renderBrowse);

  function renderBrowse() {
    var q = searchInput.value.trim().toLowerCase();
    var cat = catFilter.value, lvl = $("#levelFilter").value;
    var rows = WORDS.filter(function (w) {
      if (cat && w.category !== cat) return false;
      if (lvl && w.level !== lvl) return false;
      if (!q) return true;
      return (w.lb + " " + w.en + " " + (w.de || "") + " " + (w.fr || "") + " " + (w.ex_lb || "")).toLowerCase().indexOf(q) >= 0;
    });
    $("#browseCount").textContent = rows.length + " word" + (rows.length === 1 ? "" : "s") +
      (rows.length > 600 ? " — showing the first 600; search or filter to narrow it down" : "");
    var grid = $("#wordGrid");
    grid.innerHTML = rows.slice(0, 600).map(function (w) {
      return '<div class="word-card">' +
        '<div class="wc-head"><span class="wc-word">' + escapeHTML(articleFor(w) + w.lb) + '</span><span class="wc-lvl">' + escapeHTML(w.level || "") + '</span></div>' +
        '<div class="wc-en">' + escapeHTML(w.en || "") + '</div>' +
        (w.ex_lb ? '<div class="wc-ex">' + boldWord(w.ex_lb, w.lb) + '</div>' : '') +
        '<div class="wc-foot"><span class="wc-cat">' + escapeHTML(w.category || w.pos || "") + '</span>' +
        '<span class="wc-acts"><button class="mini-say" type="button" data-id="' + escapeHTML(w.id) + '" aria-label="Hear ' + escapeHTML(w.lb) + '">🔊</button>' +
        '<a class="mini-link" target="_blank" rel="noopener" href="' + lodURL(w.lb) + '">LOD ↗</a></span></div>' +
        '</div>';
    }).join("");
    if (!grid.dataset.say) {
      grid.dataset.say = "1";
      grid.addEventListener("click", function (e) {
        var b = e.target.closest && e.target.closest(".mini-say");
        if (!b) return;
        var w = WORDS.filter(function (x) { return x.id === b.dataset.id; })[0];
        if (w) playAudio(w);
      });
    }
    if (!rows.length) grid.innerHTML = '<p class="muted">No word matches. Try fewer letters, or clear the topic and level filters.</p>';
    if (rows.length > 600) grid.insertAdjacentHTML("beforeend", '<p class="muted">Showing the first 600 — search or filter to see the rest.</p>');
  }

  /* ---------- stats ---------- */
  function renderStats() {
    var total = WORDS.length, seen = 0, learned = 0, due = 0, now = Date.now();
    var boxes = [0, 0, 0, 0, 0, 0];
    WORDS.forEach(function (w) {
      var p = LFStore.getCard(w.id);
      if (!p) return;
      seen++;
      boxes[Math.min(p.box, 5)]++;
      if (LFsrs.isLearned(p)) learned++;
      if (LFsrs.isDue(p, now)) due++;
    });
    $("#statTotal").textContent = total;
    $("#statSeen").textContent = seen;
    $("#statLearned").textContent = learned;
    $("#statDue").textContent = due;
    $("#statStreak").textContent = LFStore.state.streak.current || 0;

    var colors = { A1: "#2bb673", A2: "#00a1de", B1: "#5b6cff", B2: "#9b51e0" };
    $("#levelProgress").innerHTML = LEVELS.map(function (lv) {
      var inLv = WORDS.filter(function (w) { return w.level === lv; });
      var done = inLv.filter(function (w) { return LFsrs.isLearned(LFStore.getCard(w.id)); }).length;
      var pct = inLv.length ? Math.round(done / inLv.length * 100) : 0;
      return '<div class="lp-row"><span class="lp-name">' + lv + '</span>' +
        '<div class="lp-bar"><div class="lp-fill" style="width:' + pct + '%;background:' + colors[lv] + '"></div></div>' +
        '<span class="lp-val">' + done + '/' + inLv.length + '</span></div>';
    }).join("");

    var max = Math.max.apply(null, boxes.concat([1]));
    $("#boxChart").innerHTML = boxes.map(function (n, i) {
      var h = Math.round(n / max * 100);
      return '<div class="box-col"><div class="box-bar" style="height:' + h + '%" title="' + n + ' cards"></div>' +
        '<span class="box-lab">' + (i === 0 ? "Again" : "B" + i) + '</span></div>';
    }).join("");
  }

  /* ---------- settings: import / export ---------- */
  function download(name, text) {
    var blob = new Blob([text], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a"); a.href = url; a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }
  $("#exportBtn").addEventListener("click", function () {
    var d = new Date().toISOString().slice(0, 10);
    download("luxflash-progress-" + d + ".json", LFStore.export());
    ioMsg("Backup downloaded ✓", true);
  });
  $("#importFile").addEventListener("change", function (e) {
    var file = e.target.files[0]; if (!file) return;
    var reader = new FileReader();
    reader.onload = function () {
      try {
        var n = LFStore.import(reader.result, "merge");
        ioMsg("Imported & merged — " + n + " cards now tracked ✓", true);
        refreshFromStore(); toast("Progress imported");
      } catch (err) {
        ioMsg("Import failed: " + err.message, false);
      }
      e.target.value = "";
    };
    reader.readAsText(file);
  });
  function ioMsg(t, ok) {
    var el = $("#ioMsg"); el.textContent = t;
    el.style.color = ok ? "var(--good)" : "var(--again)";
  }
  var newLimit = $("#newLimit");
  newLimit.value = LFStore.settings().newPerSession;
  $("#newLimitVal").textContent = newLimit.value;
  newLimit.addEventListener("input", function () {
    $("#newLimitVal").textContent = newLimit.value;
    LFStore.setSettings({ newPerSession: parseInt(newLimit.value, 10) });
  });
  $("#resetBtn").addEventListener("click", function () {
    if (!confirm("Delete ALL saved progress in this browser? Export a backup first if unsure.")) return;
    LFStore.reset(); refreshFromStore(); toast("Progress reset");
  });

  function toast(msg) {
    var el = $("#toast"); el.textContent = msg; el.hidden = false;
    requestAnimationFrame(function () { el.classList.add("show"); });
    setTimeout(function () { el.classList.remove("show"); setTimeout(function () { el.hidden = true; }, 300); }, 2200);
  }

  function refreshFromStore() {
    refreshChips();
    $("#reverseMode").checked = !!LFStore.settings().reverse;
    $("#autoPlay").checked = !!LFStore.settings().autoplay;
    newLimit.value = LFStore.settings().newPerSession;
    $("#newLimitVal").textContent = newLimit.value;
    studyAhead = false; buildSession(); nextCard();
    renderStats();
  }

  /* ---------- boot ---------- */
  function boot() {
    if (WORDS.length === 0) {
      $("#frontWord").textContent = "No data loaded";
      $("#frontExample").textContent = "data/words.js is missing or empty.";
      return;
    }
    refreshChips();
    $("#reverseMode").checked = !!LFStore.settings().reverse;
    $("#autoPlay").checked = !!LFStore.settings().autoplay;
    buildSession();
    nextCard();
    if (!LFStore.available) {
      toast("⚠️ Progress can't be saved in this browser (private mode?)");
    }
  }
  boot();

  /* ---------- account (luxsync): progress on every device ---------- */
  // Two copies of the deck become one card by card: the record reviewed last
  // wins (then the one further along). Settings stay this device's own; the
  // streak keeps the longer run.
  function mergeLF(local, remote) {
    var out = JSON.parse(JSON.stringify(local || {}));
    out.cards = out.cards || {};
    var rc = (remote && remote.cards) || {};
    Object.keys(rc).forEach(function (id) {
      var a = out.cards[id], b = rc[id];
      if (!a) { out.cards[id] = b; return; }
      var la = a.last || 0, lb = b.last || 0;
      if (lb > la || (lb === la && ((b.box || 0) > (a.box || 0) || (b.reps || 0) > (a.reps || 0)))) out.cards[id] = b;
    });
    var rs = (remote && remote.streak) || {}, ls = out.streak || {};
    if ((rs.lastDay || '') > (ls.lastDay || '')) out.streak = Object.assign({}, rs, { longest: Math.max(rs.longest || 0, ls.longest || 0) });
    else if (out.streak) out.streak.longest = Math.max(ls.longest || 0, rs.longest || 0);
    return out;
  }
  function startSync() {
    if (!window.LuxSync) return;
    var mount = $("#syncMount");
    LuxSync.start({ app: "luxflash", collect: function () { return LFStore.state; },
      apply: function (st) { LFStore.replaceState(st); refreshFromStore(); },
      merge: mergeLF, mount: mount, lang: (navigator.language || "en").slice(0, 2) === "ru" ? "ru" : "en" });
    window.addEventListener("lf:saved", function () { LuxSync.changed(); });
  }
  if (window.LuxSync) startSync(); else window.addEventListener("load", startSync);
})();
