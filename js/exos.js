/* CEFI2 — rendu des exercices corrigés (données : js/exos-data.js, générées par tools/verif.py). */
(function () {
  "use strict";
  var data = window.CEFI_EXOS;
  var list = document.getElementById("exo-list");
  if (!data || !list) return;
  var Store = window.CefiStore;
  var filter = "all";

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  function stepHtml(title, body, cls) {
    return '<div class="step ' + (cls || "") + '"><button type="button" aria-expanded="false">' + title +
      '</button><div class="sbody">' + body + "</div></div>";
  }

  function render() {
    var html = "";
    data.exos.forEach(function (e) {
      if (filter !== "all" && String(e.partie) !== filter) return;
      var done = !!Store.get("exos", e.id);
      html += '<details class="fold exo" id="' + e.id + '">' +
        '<summary><span class="badge">P' + e.partie + " · Ex " + e.num + "</span>" +
        '<span style="flex:1">' + esc(e.titre) + "</span>" +
        (done ? '<span class="check" aria-label="fait">✓</span>' : "") + "</summary><div class=\"body\">";
      html += '<div class="exo-head">' + e.tags.map(function (t) { return '<span class="badge">' + esc(t) + "</span>"; }).join("") + "</div>";
      html += "<h3>Énoncé (reformulé)</h3>" + e.enonce;
      html += '<div class="info"><p>Fais l\'exercice sur papier, puis dévoile la correction étape par étape.</p></div>';
      html += '<div class="btnrow"><button type="button" class="btn" data-act="next">Étape suivante</button>' +
        '<button type="button" class="btn" data-act="all">Tout afficher</button>' +
        '<button type="button" class="btn" data-act="none">Tout masquer</button></div>';
      e.etapes.forEach(function (s) { html += stepHtml(s.t, s.h); });
      html += stepHtml("✅ Conclusion (rédigée comme à l'examen)", e.conclusion, "concl");
      if (e.notes.length) {
        html += stepHtml("⚠️ Hypothèses et variantes", "<ul>" + e.notes.map(function (n) { return "<li>" + n + "</li>"; }).join("") + "</ul>");
      }
      html += '<label class="done-toggle"><input type="checkbox" data-exo="' + e.id + '"' + (done ? " checked" : "") +
        "> Exercice fait et compris</label>";
      html += "</div></details>";
    });
    list.innerHTML = html || '<p class="muted">Aucun exercice.</p>';
    updateCount();
  }

  function setOpen(step, open) {
    step.classList.toggle("open", open);
    step.querySelector("button").setAttribute("aria-expanded", open ? "true" : "false");
  }

  list.addEventListener("click", function (ev) {
    var b = ev.target.closest("button");
    if (!b) return;
    var body = b.closest(".body");
    if (b.parentElement.classList.contains("step")) {
      var st = b.parentElement;
      setOpen(st, !st.classList.contains("open"));
      return;
    }
    var act = b.getAttribute("data-act");
    if (!act || !body) return;
    var steps = Array.prototype.slice.call(body.querySelectorAll(".step"));
    if (act === "all") steps.forEach(function (s) { setOpen(s, true); });
    if (act === "none") steps.forEach(function (s) { setOpen(s, false); });
    if (act === "next") {
      var nxt = steps.filter(function (s) { return !s.classList.contains("open"); })[0];
      if (nxt) { setOpen(nxt, true); nxt.scrollIntoView({ behavior: "smooth", block: "nearest" }); }
    }
  });

  list.addEventListener("change", function (ev) {
    var cb = ev.target;
    if (!cb.matches("input[data-exo]")) return;
    var id = cb.getAttribute("data-exo");
    Store.set("exos", id, cb.checked ? true : null);
    var sum = document.querySelector("#" + id + " > summary");
    var mark = sum.querySelector(".check");
    if (cb.checked && !mark) sum.insertAdjacentHTML("beforeend", '<span class="check" aria-label="fait">✓</span>');
    if (!cb.checked && mark) mark.remove();
    updateCount();
  });

  function updateCount() {
    var el = document.getElementById("exo-count");
    if (!el) return;
    var n = Object.keys(Store.all("exos")).length;
    el.textContent = n + " / " + data.exos.length + " exercices faits";
  }

  document.querySelectorAll("[data-filter]").forEach(function (c) {
    c.addEventListener("click", function () {
      filter = c.getAttribute("data-filter");
      document.querySelectorAll("[data-filter]").forEach(function (o) { o.setAttribute("aria-pressed", o === c ? "true" : "false"); });
      render();
    });
  });

  render();

  /* lien direct : exercices.html#p2e3 */
  function openHash() {
    var id = location.hash.slice(1);
    if (!id) return;
    var el = document.getElementById(id);
    if (el && el.tagName === "DETAILS") { el.open = true; el.scrollIntoView(); }
  }
  window.addEventListener("hashchange", openHash);
  openHash();
})();
