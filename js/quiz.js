/* CEFI2 — moteur de quiz (aléatoire, score, révision des erreurs). */
(function () {
  "use strict";
  var BANK = window.CEFI_QUIZ || [];
  var Store = window.CefiStore;
  var $ = function (id) { return document.getElementById(id); };
  var setup = $("q-setup"), play = $("q-play"), end = $("q-end");
  if (!setup) return;

  var cfg = { part: "all", n: 10 };
  var run = null;

  function shuffle(a) {
    a = a.slice();
    for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; }
    return a;
  }
  function wrongIds() { return Object.keys(Store.all("quizWrong")); }
  function pool() {
    if (cfg.part === "wrong") { var w = wrongIds(); return BANK.filter(function (q) { return w.indexOf(q.id) >= 0; }); }
    return BANK.filter(function (q) { return cfg.part === "all" || String(q.p) === cfg.part; });
  }
  function show(el) { [setup, play, end].forEach(function (x) { x.hidden = x !== el; }); window.scrollTo(0, 0); }

  function refreshSetup() {
    var p = pool();
    $("q-avail").textContent = p.length + " question" + (p.length > 1 ? "s" : "") + " disponible" + (p.length > 1 ? "s" : "");
    $("q-start").disabled = p.length === 0;
    var nw = wrongIds().length;
    $("q-wrong-n").textContent = nw;
    var best = Store.get("quiz", "best");
    $("q-best").textContent = best ? "Meilleur score : " + best.s + " / " + best.n + " (" + Math.round(100 * best.s / best.n) + " %)" : "Pas encore de score enregistré.";
  }

  function bindChips(attr, key) {
    document.querySelectorAll("[" + attr + "]").forEach(function (c) {
      c.addEventListener("click", function () {
        var v = c.getAttribute(attr);
        cfg[key] = key === "n" ? Number(v) : v;
        document.querySelectorAll("[" + attr + "]").forEach(function (o) { o.setAttribute("aria-pressed", o === c ? "true" : "false"); });
        refreshSetup();
      });
    });
  }
  bindChips("data-part", "part");
  bindChips("data-n", "n");

  $("q-start").addEventListener("click", function () {
    var p = shuffle(pool());
    if (cfg.n > 0) p = p.slice(0, cfg.n);
    run = { qs: p, i: 0, score: 0, answered: false };
    show(play);
    renderQ();
  });

  function renderQ() {
    var q = run.qs[run.i];
    run.answered = false;
    $("q-count").textContent = "Question " + (run.i + 1) + " / " + run.qs.length;
    $("q-score").textContent = "Score : " + run.score;
    $("q-bar").style.width = (100 * run.i / run.qs.length) + "%";
    $("q-part").textContent = "Partie " + q.p;
    $("q-text").textContent = q.q;
    var order = shuffle(q.o.map(function (_, k) { return k; }));
    var box = $("q-opts");
    box.innerHTML = "";
    order.forEach(function (k) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "opt"; b.textContent = q.o[k];
      b.setAttribute("data-k", k);
      b.addEventListener("click", function () { answer(k); });
      box.appendChild(b);
    });
    $("q-expl").hidden = true;
    $("q-next").hidden = true;
  }

  function answer(k) {
    if (run.answered) return;
    run.answered = true;
    var q = run.qs[run.i];
    var ok = k === q.a;
    if (ok) run.score++;
    Store.set("quizWrong", q.id, ok ? null : true);
    document.querySelectorAll("#q-opts .opt").forEach(function (b) {
      var bk = Number(b.getAttribute("data-k"));
      b.disabled = true;
      if (bk === q.a) b.classList.add("ok");
      else if (bk === k) b.classList.add("ko");
    });
    var ex = $("q-expl");
    ex.className = "expl " + (ok ? "key" : "trap");
    ex.innerHTML = "<p><b>" + (ok ? "✓ Bonne réponse." : "✗ Raté.") + "</b> " + escapeHtml(q.e) + "</p>";
    ex.hidden = false;
    $("q-score").textContent = "Score : " + run.score;
    var nx = $("q-next");
    nx.textContent = run.i + 1 < run.qs.length ? "Question suivante →" : "Voir le score";
    nx.hidden = false;
    nx.focus({ preventScroll: true });
    ex.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
  function escapeHtml(s) { return String(s).replace(/[&<>]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]; }); }

  $("q-next").addEventListener("click", function () {
    run.i++;
    if (run.i < run.qs.length) { renderQ(); return; }
    finish();
  });

  function finish() {
    var n = run.qs.length, s = run.score;
    $("q-final").textContent = s + " / " + n;
    var pc = Math.round(100 * s / n);
    $("q-final-msg").textContent = pc >= 85 ? "Excellent, tu es prêt·e." : pc >= 60 ? "Bien. Revois les questions ratées." : "Relis les fiches puis refais un quiz « mes erreurs ».";
    var best = Store.get("quiz", "best");
    if (n >= 10 && (!best || s / n > best.s / best.n || (s / n === best.s / best.n && n > best.n))) Store.set("quiz", "best", { s: s, n: n });
    var hist = Store.get("quiz", "history") || [];
    hist.push({ s: s, n: n, d: new Date().toISOString().slice(0, 10) });
    Store.set("quiz", "history", hist.slice(-20));
    show(end);
  }

  $("q-again").addEventListener("click", function () { refreshSetup(); show(setup); });
  $("q-quit").addEventListener("click", function () { refreshSetup(); show(setup); });

  refreshSetup();
  show(setup);
})();
