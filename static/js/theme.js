/* Promptly theme — dark ⇄ light with persistence and system preference */
(function (global) {
  "use strict";

  var THEME_KEY = "promptly-theme";
  var META_NAME = "theme-color";
  var DARK_BG = "#0a0a0f";
  var LIGHT_BG = "#f6f6f9";

  function readStored() {
    try {
      var t = localStorage.getItem(THEME_KEY);
      if (t === "dark" || t === "light") return t;
    } catch (e) {}
    return null;
  }

  function systemTheme() {
    return global.matchMedia && global.matchMedia("(prefers-color-scheme: light)").matches
      ? "light"
      : "dark";
  }

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  }

  function updateMeta(theme) {
    var meta = document.querySelector('meta[name="' + META_NAME + '"]');
    if (meta) meta.setAttribute("content", theme === "light" ? LIGHT_BG : DARK_BG);
  }

  function syncToggleState() {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    var theme = currentTheme();
    btn.setAttribute("aria-pressed", theme === "light" ? "true" : "false");
  }

  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    updateMeta(theme);
    syncToggleState();
  }

  function setTheme(theme, persist) {
    apply(theme);
    if (persist !== false) {
      try { localStorage.setItem(THEME_KEY, theme); } catch (e) {}
      document.cookie =
        THEME_KEY + "=" + theme + "; path=/; max-age=31536000; samesite=Lax";
    }
  }

  function toggle() {
    setTheme(currentTheme() === "light" ? "dark" : "light");
  }

  var api = {
    init: function () {
      // The inline <head> script already applied the correct theme before paint;
      // this re-asserts it and syncs the toggle's ARIA state.
      var theme = readStored() || systemTheme();
      apply(theme);

      var btn = document.getElementById("theme-toggle");
      if (btn) btn.addEventListener("click", toggle);

      if (global.matchMedia) {
        var mq = global.matchMedia("(prefers-color-scheme: light)");
        var onChange = function (e) {
          if (!readStored()) apply(e.matches ? "light" : "dark");
        };
        if (mq.addEventListener) mq.addEventListener("change", onChange);
        else if (mq.addListener) mq.addListener(onChange);
      }
    },
    toggle: toggle,
    set: setTheme,
    get: currentTheme,
  };

  global.PromptlyTheme = api;

  document.addEventListener("DOMContentLoaded", function () {
    api.init();
  });
})(window);
