/* CEFI2 — fonctions communes : thème, progression, navigation, hors ligne. */
(function () {
  "use strict";
  var KEY = "cefi2-progress";

  /* ---------- stockage (toujours protégé) ---------- */
  function load() {
    try {
      var raw = localStorage.getItem(KEY);
      var d = raw ? JSON.parse(raw) : {};
      return d && typeof d === "object" ? d : {};
    } catch (e) { return {}; }
  }
  function save(d) {
    try { localStorage.setItem(KEY, JSON.stringify(d)); } catch (e) { /* mode privé : on ignore */ }
  }
  var Store = {
    get: function (section, id) { var d = load(); return d[section] ? d[section][id] : undefined; },
    set: function (section, id, value) {
      var d = load(); d[section] = d[section] || {};
      if (value === undefined || value === null || value === false) delete d[section][id];
      else d[section][id] = value;
      save(d);
    },
    all: function (section) { var d = load(); return d[section] || {}; },
    reset: function () { try { localStorage.removeItem(KEY); } catch (e) {} }
  };
  window.CefiStore = Store;

  /* ---------- thème ---------- */
  function currentTheme() {
    var t = document.documentElement.getAttribute("data-theme");
    if (t) return t;
    return window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function paintToggle(btn) {
    var dark = currentTheme() === "dark";
    btn.textContent = dark ? "☀︎" : "☾";
    btn.setAttribute("aria-label", dark ? "Passer en mode clair" : "Passer en mode sombre");
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", dark ? "#121418" : "#f6f5f1");
  }

  /* ---------- formatage numérique partagé ---------- */
  window.cefiFmt = function (x, d) {
    d = d || 0;
    if (!isFinite(x)) return "—";
    var v = Math.round(Math.abs(x) * Math.pow(10, d)) / Math.pow(10, d);
    var s = v.toFixed(d).split(".");
    s[0] = s[0].replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    var out = s.join(",");
    return (x < 0 && v !== 0 ? "−" : "") + out;
  };

  document.addEventListener("DOMContentLoaded", function () {
    /* bouton thème */
    var btn = document.getElementById("theme-btn");
    if (btn) {
      paintToggle(btn);
      btn.addEventListener("click", function () {
        var next = currentTheme() === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        try { localStorage.setItem("cefi2-theme", next); } catch (e) {}
        paintToggle(btn);
      });
    }

    /* onglet courant */
    var page = document.body.getAttribute("data-page");
    document.querySelectorAll(".tabs a").forEach(function (a) {
      if (a.getAttribute("data-page") === page) a.setAttribute("aria-current", "page");
    });

    /* cases "revu" */
    document.querySelectorAll("input[data-done]").forEach(function (cb) {
      var id = cb.getAttribute("data-done");
      cb.checked = !!Store.get("fiches", id);
      cb.addEventListener("change", function () {
        Store.set("fiches", id, cb.checked ? true : null);
        document.dispatchEvent(new CustomEvent("cefi:progress"));
      });
    });

    /* indicateur hors ligne */
    function net() { document.body.classList.toggle("offline", !navigator.onLine); }
    window.addEventListener("online", net);
    window.addEventListener("offline", net);
    net();
  });

  /* ---------- service worker ---------- */
  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("sw.js").catch(function () {});
    });
  }
})();
