/* CEFI2 — mini-calculateurs (VAN/IP/délai, seuil de rentabilité, TCO).
   Mêmes conventions que tools/verif.py : flux actualisés arrondis à l'euro. */
(function () {
  "use strict";
  var fmt = function (x, d) { return window.cefiFmt(x, d); };
  var $ = function (id) { return document.getElementById(id); };

  /* "1 200,5 ; 300" -> [1200.5, 300]. Séparateurs : ; retour à la ligne, tabulation, ou espace
     entre deux nombres ; la virgule est décimale. Espaces de milliers acceptés ("1 200 000"). */
  function parseList(s) {
    var parts = String(s).split(/[;\n\t]+/);
    var out = [];
    parts.forEach(function (p) {
      p = p.trim();
      if (!p) return;
      var compact = p.replace(/[\s  ]/g, "");
      if (/^[-−+]?\d+([.,]\d+)?$/.test(compact) && /^\S+(?:[\s  ]\d{3})+(?:[.,]\d+)?$/.test(p)) {
        out.push(num(compact)); return;            // nombre avec espaces de milliers
      }
      p.split(/[\s  ]+/).forEach(function (q) { if (q) out.push(num(q)); });
    });
    return out;
  }
  function num(s) { return Number(String(s).replace(/[\s  ]/g, "").replace("−", "-").replace(",", ".")); }
  function val(id) { return num($(id).value); }
  function rnd(x) { return x < 0 ? -Math.round(-x) : Math.round(x); }
  function err(box, msg) { box.innerHTML = '<p class="trap">' + msg + "</p>"; }
  function remember(ids) {
    ids.forEach(function (id) {
      var el = $(id);
      try { var v = localStorage.getItem("cefi2-calc-" + id); if (v !== null) el.value = v; } catch (e) {}
      el.addEventListener("input", function () { try { localStorage.setItem("cefi2-calc-" + id, el.value); } catch (e) {} });
    });
  }

  /* ---------------- VAN / IP / délai ---------------- */
  function van(flows, i) { return flows.reduce(function (s, f, t) { return s + f / Math.pow(1 + i, t); }, 0); }
  function tri(flows) {
    var lo = -0.99, hi = 10;
    if (van(flows, lo) * van(flows, hi) > 0) return null;
    for (var k = 0; k < 200; k++) {
      var mid = (lo + hi) / 2;
      if (van(flows, lo) * van(flows, mid) <= 0) hi = mid; else lo = mid;
    }
    return (lo + hi) / 2;
  }
  function payback(flows) {
    var cum = 0;
    for (var t = 0; t < flows.length; t++) {
      var prev = cum; cum += flows[t];
      if (t > 0 && prev < 0 && cum >= 0) return (t - 1) + (-prev) / flows[t];
    }
    return null;
  }
  function dureeTxt(d) {
    if (d === null) return "non récupéré sur la période";
    var an = Math.floor(d), mf = (d - an) * 12, m = Math.floor(mf), j = Math.round((mf - m) * 30);
    if (j === 30) { m++; j = 0; }
    if (m === 12) { an++; m = 0; }
    return fmt(d, 2) + " ans ≈ " + an + " an" + (an > 1 ? "s" : "") + (m ? " " + m + " mois" : "") + (j ? " " + j + " j" : "");
  }

  function calcVan() {
    var box = $("v-out");
    var i0 = Math.abs(val("v-i0")), i = val("v-rate") / 100;
    var fl = parseList($("v-flows").value);
    if (!isFinite(i0) || i0 === 0) return err(box, "Indique l'investissement initial.");
    if (!isFinite(i) || i <= -1) return err(box, "Taux d'actualisation invalide.");
    if (!fl.length || fl.some(function (x) { return !isFinite(x); })) return err(box, "Liste de flux invalide (sépare les années par ; ou par un retour à la ligne).");
    var flows = [-i0].concat(fl);
    var rows = "", cum = 0, cumA = 0, sumAct = 0, vMill = -i0;
    flows.forEach(function (f, t) {
      var c = Math.pow(1 + i, -t), fa = rnd(f * c);
      cum += f; cumA += fa;
      if (t > 0) { sumAct += fa; vMill += rnd(f * Math.round(c * 1000) / 1000); }
      rows += "<tr><th>A" + t + "</th><td class=\"n" + (f < 0 ? " neg" : "") + "\">" + fmt(f) + "</td><td class=\"n" + (cum < 0 ? " neg" : "") + "\">" + fmt(cum) +
        "</td><td class=\"n\">" + fmt(c, 3) + "</td><td class=\"n" + (fa < 0 ? " neg" : "") + "\">" + fmt(fa) + "</td><td class=\"n" + (cumA < 0 ? " neg" : "") + "\">" + fmt(cumA) + "</td></tr>";
    });
    var V = sumAct - i0, ip = sumAct / i0, d = payback(flows);
    var actFlows = flows.map(function (f, t) { return rnd(f * Math.pow(1 + i, -t)); });
    var dAct = payback(actFlows), r = tri(flows);
    box.innerHTML =
      '<dl class="kv">' +
      "<dt>VAN</dt><dd class=\"big\">" + fmt(V) + " €</dd>" +
      "<dt>IP</dt><dd>" + fmt(ip, 3) + "</dd>" +
      "<dt>Délai de récupération</dt><dd>" + dureeTxt(d) + "</dd>" +
      "<dt>Σ flux actualisés</dt><dd>" + fmt(sumAct) + " €</dd>" +
      "<dt>VAN (coef. au millième)</dt><dd>" + fmt(vMill) + " €</dd>" +
      "<dt>TRI <span class=\"tag\">complément</span></dt><dd>" + (r === null ? "—" : fmt(r * 100, 2) + " %") + "</dd>" +
      "<dt>Délai actualisé <span class=\"tag\">complément</span></dt><dd>" + dureeTxt(dAct) + "</dd>" +
      "</dl>" +
      '<div class="tw"><table><thead><tr><th>Année</th><th>Flux</th><th>Cumul</th><th>Coef.</th><th>Actualisé</th><th>Cumul act.</th></tr></thead><tbody>' + rows + "</tbody></table></div>" +
      '<p class="muted">' + (V > 0 ? "VAN > 0 : le projet est rentable au taux de " + fmt(i * 100, 2) + " %." : V < 0 ? "VAN < 0 : le projet ne couvre pas le coût des capitaux." : "VAN nulle : le TRI est égal au taux.") + "</p>";
  }

  /* ---------------- Seuil de rentabilité ---------------- */
  function calcSr() {
    var box = $("s-out");
    var mode = document.querySelector('input[name="s-mode"]:checked').value;
    var cf = val("s-cf");
    if (!isFinite(cf) || cf < 0) return err(box, "Charges fixes invalides.");
    var html = '<dl class="kv">';
    if (mode === "global") {
      var ca = val("s-ca"), cv = val("s-cv");
      if (!(ca > 0) || !isFinite(cv)) return err(box, "Indique le CA et les coûts variables.");
      var mcv = ca - cv, tm = mcv / ca;
      if (tm <= 0) return err(box, "Marge sur coût variable négative ou nulle : pas de seuil.");
      var sr = cf / tm, ms = ca - sr;
      html += "<dt>MCV</dt><dd>" + fmt(mcv) + " €</dd><dt>TMCV</dt><dd>" + fmt(tm * 100, 2) + " %</dd>" +
        "<dt>Seuil de rentabilité</dt><dd class=\"big\">" + fmt(sr) + " €</dd>" +
        "<dt>Résultat</dt><dd>" + fmt(mcv - cf) + " €</dd>" +
        "<dt>Marge de sécurité</dt><dd>" + fmt(ms) + " € (" + fmt(ms / ca * 100, 1) + " %)</dd>";
    } else {
      var pu = val("s-pu"), cvu = val("s-cvu"), q = val("s-q");
      if (!(pu > 0) || !isFinite(cvu)) return err(box, "Indique le prix et le coût variable unitaires.");
      var m = pu - cvu;
      if (m <= 0) return err(box, "Marge unitaire négative ou nulle : pas de seuil.");
      var qs = cf / m;
      html += "<dt>MCV unitaire</dt><dd>" + fmt(m, 2) + " €</dd><dt>TMCV</dt><dd>" + fmt(m / pu * 100, 2) + " %</dd>" +
        "<dt>Seuil en quantité</dt><dd class=\"big\">" + fmt(qs, 2) + " → " + Math.ceil(qs - 1e-9) + "</dd>" +
        "<dt>Seuil en valeur</dt><dd>" + fmt(qs * pu) + " €</dd>";
      if (q > 0) html += "<dt>Résultat pour " + fmt(q) + "</dt><dd>" + fmt(q * m - cf) + " €</dd>" +
        "<dt>Marge de sécurité</dt><dd>" + fmt((q - qs) / q * 100, 1) + " %</dd>";
    }
    box.innerHTML = html + "</dl>";
  }
  function srMode() {
    var g = document.querySelector('input[name="s-mode"]:checked').value === "global";
    $("s-global").hidden = !g; $("s-unit").hidden = g;
    try { localStorage.setItem("cefi2-calc-s-mode", g ? "global" : "unit"); } catch (e) {}
  }

  /* ---------------- TCO ---------------- */
  function calcTco() {
    var box = $("t-out");
    var vols = parseList($("t-vol").value);
    var n = Math.round(val("t-n"));
    if (!(n > 0)) return err(box, "Indique la durée (années).");
    if (!vols.length) vols = [0];
    while (vols.length < n) vols.push(vols[vols.length - 1]);
    var S = ["a", "b"].map(function (k) {
      return { b: val("t-" + k + "b") || 0, f: val("t-" + k + "f") || 0, v: val("t-" + k + "v") || 0 };
    });
    var rows = "", cum = [S[0].b, S[1].b], cross = null;
    rows += "<tr><th>Build</th><td class=\"n\"></td><td class=\"n\">" + fmt(cum[0]) + "</td><td class=\"n\">" + fmt(cum[1]) + "</td></tr>";
    for (var t = 0; t < n; t++) {
      var prevLead = cum[0] <= cum[1] ? 0 : 1;
      for (var k = 0; k < 2; k++) cum[k] += S[k].f + S[k].v * vols[t];
      var lead = cum[0] <= cum[1] ? 0 : 1;
      if (cross === null && lead !== prevLead) cross = t + 1;
      rows += "<tr><th>A" + (t + 1) + "</th><td class=\"n\">" + fmt(vols[t]) + "</td><td class=\"n\">" + fmt(cum[0]) + "</td><td class=\"n\">" + fmt(cum[1]) + "</td></tr>";
    }
    var best = cum[0] < cum[1] ? "A" : cum[1] < cum[0] ? "B" : null;
    box.innerHTML = '<dl class="kv"><dt>TCO A</dt><dd class="big">' + fmt(cum[0]) + "</dd><dt>TCO B</dt><dd class=\"big\">" + fmt(cum[1]) +
      "</dd><dt>Écart</dt><dd>" + fmt(Math.abs(cum[0] - cum[1])) + (best ? " en faveur de " + best : "") + "</dd>" +
      (cross ? "<dt>Inversion</dt><dd>l'ordre change en année " + cross + "</dd>" : "") + "</dl>" +
      '<div class="tw"><table><thead><tr><th>Cumul</th><th>Volume</th><th>A</th><th>B</th></tr></thead><tbody>' + rows + "</tbody></table></div>";
  }

  document.addEventListener("DOMContentLoaded", function () {
    remember(["v-i0", "v-rate", "v-flows", "s-ca", "s-cv", "s-cf", "s-pu", "s-cvu", "s-q",
      "t-n", "t-vol", "t-ab", "t-af", "t-av", "t-bb", "t-bf", "t-bv"]);
    try { var m = localStorage.getItem("cefi2-calc-s-mode"); if (m) document.querySelector('input[name="s-mode"][value="' + m + '"]').checked = true; } catch (e) {}
    srMode();
    document.querySelectorAll('input[name="s-mode"]').forEach(function (r) { r.addEventListener("change", function () { srMode(); calcSr(); }); });
    $("v-go").addEventListener("click", calcVan);
    $("s-go").addEventListener("click", calcSr);
    $("t-go").addEventListener("click", calcTco);
    document.querySelectorAll("[data-example]").forEach(function (b) {
      b.addEventListener("click", function () {
        var ex = JSON.parse(b.getAttribute("data-example"));
        Object.keys(ex).forEach(function (id) {
          if (id === "mode") { document.querySelector('input[name="s-mode"][value="' + ex.mode + '"]').checked = true; srMode(); return; }
          $(id).value = ex[id]; $(id).dispatchEvent(new Event("input"));
        });
        ({ v: calcVan, s: calcSr, t: calcTco })[b.getAttribute("data-calc")]();
      });
    });
  });
  window.CefiCalc = { parseList: parseList };
})();
