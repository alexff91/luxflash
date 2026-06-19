/* LuxFlash storage layer — all progress lives in the browser (localStorage).
   Exposes window.LFStore. */
(function () {
  "use strict";

  var KEY = "luxflash.v1";
  var SCHEMA = 1;

  function todayStr(d) {
    d = d || new Date();
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }

  function defaults() {
    return {
      schema: SCHEMA,
      app: "luxflash",
      createdAt: Date.now(),
      updatedAt: Date.now(),
      settings: { levels: ["A1", "A2"], newPerSession: 20, reverse: false, theme: null },
      streak: { current: 0, longest: 0, lastDay: null },
      cards: {} // id -> { box, due, reps, lapses, last }
    };
  }

  var state = load();

  function load() {
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return defaults();
      var data = JSON.parse(raw);
      return migrate(data);
    } catch (e) {
      console.warn("LuxFlash: could not read saved progress, starting fresh.", e);
      return defaults();
    }
  }

  function migrate(data) {
    if (!data || typeof data !== "object") return defaults();
    var d = defaults();
    // shallow merge to tolerate older/partial files
    d.settings = Object.assign(d.settings, data.settings || {});
    d.streak = Object.assign(d.streak, data.streak || {});
    d.cards = (data.cards && typeof data.cards === "object") ? data.cards : {};
    if (data.createdAt) d.createdAt = data.createdAt;
    d.schema = SCHEMA;
    return d;
  }

  var saveTimer = null;
  function save() {
    state.updatedAt = Date.now();
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
    } catch (e) {
      console.warn("LuxFlash: save failed (storage full or blocked).", e);
    }
  }
  function saveDebounced() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(save, 250);
  }

  window.LFStore = {
    get state() { return state; },
    settings: function () { return state.settings; },
    getCard: function (id) { return state.cards[id] || null; },
    setCard: function (id, prog) { state.cards[id] = prog; saveDebounced(); },
    setSettings: function (patch) { Object.assign(state.settings, patch); saveDebounced(); },

    /* streak handling — call once when a review is completed */
    touchStreak: function () {
      var t = todayStr();
      var s = state.streak;
      if (s.lastDay === t) return s.current;
      var yest = todayStr(new Date(Date.now() - 86400000));
      s.current = (s.lastDay === yest) ? s.current + 1 : 1;
      s.lastDay = t;
      if (s.current > s.longest) s.longest = s.current;
      saveDebounced();
      return s.current;
    },

    saveNow: save,

    /* ---- import / export ---- */
    export: function () {
      return JSON.stringify(state, null, 2);
    },
    import: function (text, mode) {
      var incoming = JSON.parse(text); // throws on bad JSON
      if (incoming && incoming.app && incoming.app !== "luxflash") {
        throw new Error("This file does not look like a LuxFlash backup.");
      }
      var clean = migrate(incoming);
      if (mode === "merge") {
        var merged = Object.assign({}, state.cards);
        Object.keys(clean.cards).forEach(function (id) {
          var a = merged[id], b = clean.cards[id];
          // keep the more-advanced record
          if (!a || (b.box || 0) > (a.box || 0) || (b.reps || 0) > (a.reps || 0)) merged[id] = b;
        });
        clean.cards = merged;
        if (state.streak.current > clean.streak.current) clean.streak = state.streak;
      }
      state = clean;
      save();
      return countCards();
    },
    reset: function () {
      state = defaults();
      save();
    }
  };

  function countCards() { return Object.keys(state.cards).length; }
})();
