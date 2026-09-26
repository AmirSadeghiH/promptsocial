/* Promptly — AI studio.
   Renders three things from one source of truth: the allowance meter, the
   result canvas, and the shelf of the user's own generations. The server
   seeds all three as JSON, so nothing here duplicates a number. */
(function () {
  "use strict";

  var config = window.PROMPTLY_STUDIO;
  if (!config) return;

  var state = readSeed();

  var form = document.getElementById("studio-form");
  var promptEl = document.getElementById("studio-prompt");
  var countEl = document.getElementById("studio-count");
  var submitBtn = document.getElementById("studio-submit");
  var errorEl = document.getElementById("studio-error");
  var canvas = document.getElementById("studio-canvas");
  var grid = document.getElementById("studio-generations");
  var refBox = document.getElementById("studio-ref");
  var refMedia = document.getElementById("studio-ref-media");
  var refText = document.getElementById("studio-ref-text");
  var refClear = document.getElementById("studio-ref-clear");

  var activeSource = null;
  var busy = false;

  function readSeed() {
    var node = document.getElementById(config.dataId);
    if (!node) return { quota: [], generations: [] };
    try {
      var parsed = JSON.parse(node.textContent);
      return { quota: parsed.quota || [], generations: parsed.generations || [] };
    } catch (e) {
      return { quota: [], generations: [] };
    }
  }

  function t(key, params) {
    return window.PromptlyI18n ? window.PromptlyI18n.t(key, params) : key;
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function toast(message) {
    var box = document.getElementById("toast");
    if (!box) return;
    box.textContent = message;
    box.classList.add("show");
    setTimeout(function () { box.classList.remove("show"); }, 2200);
  }

  function getCookie(name) {
    var row = document.cookie.split("; ").find(function (part) {
      return part.indexOf(name + "=") === 0;
    });
    return row ? row.split("=")[1] : "";
  }

  function formatDuration(seconds) {
    var total = Math.max(0, parseInt(seconds, 10) || 0);
    if (!total) return "";
    var days = Math.floor(total / 86400);
    var hours = Math.floor((total % 86400) / 3600);
    var minutes = Math.max(1, Math.round((total % 3600) / 60));
    if (days > 0) return t("studio_duration_days", { d: days, h: hours });
    if (hours > 0) return t("studio_duration_hours", { h: hours, m: minutes });
    return t("studio_duration_minutes", { m: minutes });
  }

  /* ---------------- Allowance meter ---------------- */

  function renderQuota(quota) {
    if (!quota || !quota.length) return;
    quota.forEach(function (entry) {
      var row = document.querySelector('.quota-row[data-quota-key="' + entry.key + '"]');
      if (!row) return;

      row.dataset.used = entry.used;
      row.dataset.limit = entry.limit;
      row.classList.toggle("is-full", entry.remaining <= 0);

      var value = row.querySelector(".quota-value");
      if (value) value.innerHTML = "<b>" + entry.used + "</b><span>/" + entry.limit + "</span>";

      var fill = row.querySelector(".quota-fill");
      if (fill) fill.style.width = entry.percent + "%";

      var bar = row.querySelector(".quota-bar");
      if (bar) bar.setAttribute("aria-label", entry.used + " / " + entry.limit);

      var reset = row.querySelector(".quota-reset");
      if (reset) {
        var left = formatDuration(entry.reset_in_seconds);
        reset.textContent = left ? t("studio_quota_resets", { d: left }) : "";
      }
    });
  }

  /* ---------------- Canvas ---------------- */

  function latentPlate(promptText) {
    var wrap = el("div", "studio-latent");
    var plate = el("div", "studio-latent-plate");
    plate.appendChild(el("span", "studio-latent-sweep"));
    if (promptText) plate.appendChild(el("p", "studio-latent-prompt", promptText));
    wrap.appendChild(plate);

    var foot = el("div", "studio-latent-foot");
    if (promptText) {
      foot.appendChild(el("span", "studio-latent-status", t("studio_generating")));
      foot.appendChild(el("span", "studio-latent-elapsed", t("studio_elapsed", { n: 0 })));
    } else {
      foot.appendChild(el("span", "studio-latent-hint", t("studio_canvas_empty")));
    }
    wrap.appendChild(foot);
    return wrap;
  }

  function resultCard(generation, hero) {
    var card = el("article", "generation-card" + (hero ? " generation-card-hero" : ""));
    card.dataset.id = generation.id;

    var frame = el("div", "generation-frame");
    var img = el("img");
    img.src = generation.image;
    img.alt = generation.prompt;
    img.loading = "lazy";
    img.decoding = "async";
    frame.appendChild(img);
    frame.appendChild(el("span", "generation-status is-ready", t("studio_ready")));
    card.appendChild(frame);

    var body = el("div", "generation-body");
    var prompt = el("p", "generation-prompt", generation.prompt);
    prompt.dir = "auto";
    body.appendChild(prompt);

    var foot = el("div", "generation-foot");
    foot.appendChild(el("time", "generation-time", generation.label || ""));

    var actions = el("div", "generation-actions");
    var download = el("a", "btn btn-ghost btn-sm");
    download.href = generation.image;
    download.setAttribute("download", "");
    download.textContent = t("studio_download");
    actions.appendChild(download);

    var reuse = el("button", "btn btn-outline btn-sm");
    reuse.type = "button";
    reuse.textContent = t("studio_use_again");
    reuse.addEventListener("click", function () { applyPrompt(generation.prompt, null); });
    actions.appendChild(reuse);

    foot.appendChild(actions);
    body.appendChild(foot);
    card.appendChild(body);
    return card;
  }

  function failedCard(generation) {
    var card = el("article", "generation-card is-failed");
    card.dataset.id = generation.id;

    var frame = el("div", "generation-frame generation-frame-error");
    frame.appendChild(el("span", "generation-status is-failed", t("studio_failed")));
    card.appendChild(frame);

    var body = el("div", "generation-body");
    var prompt = el("p", "generation-prompt", generation.prompt);
    prompt.dir = "auto";
    body.appendChild(prompt);
    if (generation.error) body.appendChild(el("p", "generation-error", generation.error));
    card.appendChild(body);
    return card;
  }

  function renderCanvas(generation) {
    if (!canvas) return;
    canvas.textContent = "";
    if (generation && generation.status === "ready" && generation.image) {
      canvas.appendChild(resultCard(generation, true));
    } else if (generation && generation.status === "failed") {
      canvas.appendChild(failedCard(generation));
    } else {
      canvas.appendChild(latentPlate(null));
    }
  }

  /* ---------------- My generations shelf ---------------- */

  function generationNode(generation) {
    return generation.status === "ready" && generation.image
      ? resultCard(generation, false)
      : failedCard(generation);
  }

  function renderGenerations(list) {
    if (!grid) return;
    grid.textContent = "";
    if (!list || !list.length) {
      grid.appendChild(el("p", "muted studio-empty", t("studio_no_generations")));
      return;
    }
    list.forEach(function (generation) {
      grid.appendChild(generationNode(generation));
    });
  }

  function prependGeneration(generation) {
    if (!grid) return;
    var empty = grid.querySelector(".studio-empty");
    if (empty) empty.remove();
    grid.insertBefore(generationNode(generation), grid.firstChild);
  }

  /* ---------------- Prompt input ---------------- */

  function updateCount() {
    if (!countEl || !promptEl) return;
    var length = promptEl.value.trim().length;
    countEl.textContent = length;
    // The cap is enforced on submit; show the overflow before it is refused.
    countEl.parentNode.classList.toggle("is-over", length > config.maxLength);
  }

  function clearReference() {
    activeSource = null;
    if (refBox) refBox.hidden = true;
    if (refMedia) {
      refMedia.textContent = "";
      refMedia.classList.remove("is-text");
    }
    if (refText) refText.textContent = "";
  }

  function showReference(source) {
    if (!refBox) return;
    refMedia.textContent = "";
    if (source && source.image) {
      refMedia.classList.remove("is-text");
      var thumb = el("img");
      thumb.src = source.image;
      thumb.alt = "";
      refMedia.appendChild(thumb);
    } else {
      refMedia.classList.add("is-text");
      refMedia.textContent = "¶";
    }
    if (refText) refText.textContent = source && source.text ? source.text : "";
    refBox.hidden = false;
  }

  function applyPrompt(text, source) {
    if (!promptEl) return;
    promptEl.value = text || "";
    updateCount();
    activeSource = source && source.post_id ? parseInt(source.post_id, 10) || null : null;
    if (source) {
      showReference({ image: source.image, text: text });
    } else {
      clearReference();
    }
    if (form) {
      form.scrollIntoView({ block: "center", behavior: "smooth" });
      promptEl.focus();
    }
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    return new Promise(function (resolve) {
      var area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
      resolve();
    });
  }

  /* ---------------- Errors ---------------- */

  function clearError() {
    if (!errorEl) return;
    errorEl.hidden = true;
    errorEl.textContent = "";
  }

  function showError(message, detail) {
    if (!errorEl) return;
    errorEl.hidden = false;
    errorEl.textContent = message;
    if (detail) errorEl.appendChild(el("span", "studio-error-detail", detail));
  }

  function setBusy(next) {
    busy = next;
    if (!submitBtn) return;
    submitBtn.disabled = next;
    submitBtn.classList.toggle("is-loading", next);
    if (canvas) canvas.setAttribute("aria-busy", next ? "true" : "false");
  }

  /* ---------------- Request ---------------- */

  function request(prompt) {
    return fetch(config.endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      credentials: "same-origin",
      body: JSON.stringify({ prompt: prompt, source_post_id: activeSource }),
    }).then(function (response) {
      return response
        .json()
        .catch(function () { return {}; })
        .then(function (body) { return { status: response.status, body: body }; });
    });
  }

  function handleResult(status, body) {
    if (status === 201 && body.generation) {
      renderCanvas(body.generation);
      renderQuota(body.quota);
      prependGeneration(body.generation);
      state.generations.unshift(body.generation);
      clearReference();
      toast(t("studio_done_toast"));
      return;
    }

    var code = body && body.error_code;

    if (status === 401) {
      renderCanvas(null);
      showError(t("studio_login_required"));
      setTimeout(function () { window.location.href = config.loginUrl; }, 900);
      return;
    }
    if (code === "quota_exceeded") {
      renderQuota(body.quota);
      renderCanvas(null);
      var message = t("studio_limit_" + (body.window || "day"), { n: body.limit });
      var wait = formatDuration(body.retry_after_seconds);
      if (wait) message += " " + t("studio_limit_reset", { d: wait });
      showError(message);
      return;
    }
    if (code === "invalid_prompt") {
      renderCanvas(null);
      showError(t("studio_prompt_required"));
      return;
    }

    renderCanvas(null);
    showError(t("studio_provider_error"), body && body.error);
  }

  if (form && promptEl) {
    promptEl.addEventListener("input", updateCount);

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (busy) return;

      if (!config.canGenerate) {
        showError(t("studio_login_required"));
        return;
      }

      var prompt = promptEl.value.trim();
      if (!prompt) {
        showError(t("studio_prompt_required"));
        promptEl.focus();
        return;
      }
      if (prompt.length > config.maxLength) {
        showError(t("studio_max_length", { n: config.maxLength }));
        return;
      }

      clearError();
      setBusy(true);
      if (canvas) {
        canvas.textContent = "";
        canvas.appendChild(latentPlate(prompt));
      }

      var elapsed = 0;
      var timer = setInterval(function () {
        elapsed += 1;
        if (!canvas) return;
        var node = canvas.querySelector(".studio-latent-elapsed");
        if (node) node.textContent = t("studio_elapsed", { n: elapsed });
      }, 1000);

      request(prompt)
        .then(function (result) { handleResult(result.status, result.body); })
        .catch(function () {
          renderCanvas(null);
          showError(t("studio_provider_error"));
        })
        .then(function () {
          clearInterval(timer);
          setBusy(false);
        });
    });
  }

  if (refClear) {
    refClear.addEventListener("click", function () {
      clearReference();
      if (promptEl) promptEl.focus();
    });
  }

  /* Library: copy a prompt, or send one straight into the composer. */
  document.addEventListener("click", function (event) {
    var copyBtn = event.target.closest("[data-studio-copy]");
    if (copyBtn) {
      var copyCard = copyBtn.closest("[data-prompt]");
      if (copyCard) {
        copyText(copyCard.dataset.prompt || "").then(function () { toast(t("copy_toast")); });
      }
      return;
    }

    var useBtn = event.target.closest("[data-studio-use]");
    if (useBtn) {
      var card = useBtn.closest("[data-prompt]");
      if (!card) return;
      var image = card.querySelector(".prompt-card-media img");
      applyPrompt(card.dataset.prompt || "", {
        image: image ? image.src : null,
        text: card.dataset.prompt || "",
        post_id: card.dataset.postId,
      });
    }
  });

  /* i18n.js asks pages to re-apply their own strings after a language switch. */
  window.promptlyApplyPageI18n = function () {
    renderQuota(state.quota);
    renderGenerations(state.generations);
    renderCanvas(state.generations[0] || null);
    if (submitBtn) {
      var label = submitBtn.querySelector("span");
      if (label) label.textContent = t("studio_generate");
    }
  };

  renderQuota(state.quota);
  renderGenerations(state.generations);
  renderCanvas(state.generations[0] || null);
  updateCount();
  if (submitBtn && !config.canGenerate) submitBtn.disabled = true;
})();
