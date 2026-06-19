/* LuxFlash spaced repetition — a lightweight Leitner system.
   Boxes 0..5. Each grade moves the card and schedules its next due date.
   Exposes window.LFsrs. */
(function () {
  "use strict";

  var DAY = 86400000;
  // interval (in days) a card waits after reaching each box
  var INTERVALS = [0, 1, 2, 4, 8, 16, 35];
  var MAX_BOX = 5;
  var LEARNED_BOX = 4; // box >= this counts as "learned"

  function intervalDays(box) { return INTERVALS[Math.min(box, INTERVALS.length - 1)]; }

  function fresh() { return { box: 0, due: 0, reps: 0, lapses: 0, last: 0 }; }

  // returns a human label for what each grade would schedule (for button hints)
  function preview(prog) {
    prog = prog || fresh();
    return {
      again: "<1m",
      hard: fmt(Math.max(1, Math.round(intervalDays(prog.box) * 0.6 || 1))),
      good: fmt(intervalDays(Math.min(prog.box + 1, MAX_BOX)) || 1),
      easy: fmt(Math.round((intervalDays(Math.min(prog.box + 2, MAX_BOX)) || 2) * 1.3))
    };
  }

  function fmt(days) {
    if (days < 1) return "<1d";
    if (days < 21) return days + "d";
    if (days < 60) return Math.round(days / 7) + "w";
    return Math.round(days / 30) + "mo";
  }

  // apply a grade, mutating + returning the new progress object
  function grade(prog, g) {
    prog = prog ? Object.assign({}, prog) : fresh();
    prog.reps++;
    prog.last = Date.now();
    var box = prog.box;
    switch (g) {
      case "again": box = 0; prog.lapses++; break;
      case "hard":  box = Math.max(0, box); break; // stay, short re-show
      case "good":  box = Math.min(box + 1, MAX_BOX); break;
      case "easy":  box = Math.min(box + 2, MAX_BOX); break;
    }
    prog.box = box;
    var days;
    if (g === "again") days = 0;
    else if (g === "hard") days = Math.max(0.007, intervalDays(box) * 0.6);
    else if (g === "easy") days = (intervalDays(box) || 2) * 1.3;
    else days = intervalDays(box) || 1;
    prog.due = Date.now() + days * DAY;
    return prog;
  }

  function isDue(prog, now) {
    if (!prog) return false;
    return (prog.due || 0) <= (now || Date.now());
  }
  function isLearned(prog) { return prog && prog.box >= LEARNED_BOX; }

  window.LFsrs = {
    fresh: fresh, grade: grade, preview: preview,
    isDue: isDue, isLearned: isLearned,
    LEARNED_BOX: LEARNED_BOX, MAX_BOX: MAX_BOX
  };
})();
