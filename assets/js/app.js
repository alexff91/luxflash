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
    if (i >= 0) { if (sel.length > 1) sel.splice(i, 1); }
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

  /* keyboard shortcuts */
  document.addEventListener("keydown", function (e) {
    if (/^(input|textarea|select)$/i.test(e.target.tagName)) return;
    if (!$("#view-study").classList.contains("is-active")) return;
    if (e.key === " ") { e.preventDefault(); flip(); return; }
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
  $("#studyAnywayBtn").addEventListener("click", function () {
    studyAhead = true; buildSession(); nextCard();
  });

  /* speech — no browser ships a Luxembourgish voice yet, so we prefer an
     actual lb voice if one ever exists, then fall back to German (closest
     phonetics) rather than letting it default to an English voice. */
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
  $("#speakBtn").addEventListener("click", function (e) {
    e.stopPropagation();
    if (current) speakWord(current.lb);
  });

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
    $("#browseCount").textContent = rows.length + " word" + (rows.length === 1 ? "" : "s");
    var grid = $("#wordGrid");
    grid.innerHTML = rows.slice(0, 600).map(function (w) {
      return '<div class="word-card">' +
        '<div class="wc-head"><span class="wc-word">' + escapeHTML(articleFor(w) + w.lb) + '</span><span class="wc-lvl">' + escapeHTML(w.level || "") + '</span></div>' +
        '<div class="wc-en">' + escapeHTML(w.en || "") + '</div>' +
        (w.ex_lb ? '<div class="wc-ex">' + boldWord(w.ex_lb, w.lb) + '</div>' : '') +
        '<div class="wc-foot"><span class="wc-cat">' + escapeHTML(w.category || w.pos || "") + '</span>' +
        '<a class="mini-link" target="_blank" rel="noopener" href="' + lodURL(w.lb) + '">LOD ↗</a></div>' +
        '</div>';
    }).join("");
    if (rows.length > 600) grid.insertAdjacentHTML("beforeend", '<p class="muted">Showing first 600 — refine your search.</p>');
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
        '<span class="box-lab">' + (i === 0 ? "New" : "B" + i) + '</span></div>';
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
    buildSession();
    nextCard();
  }
  boot();
})();
