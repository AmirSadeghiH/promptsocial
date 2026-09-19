/* Promptly i18n — client-side English ⇄ Persian */
(function (global) {
  "use strict";

  var STRINGS = {
    en: {
      search_placeholder: "Search prompts...",
      toggle_theme: "Toggle dark or light mode",
      switch_language: "Switch language",
      lang_switch_label: "FA",
      create: "Create",
      login: "Log in",
      signup: "Sign up",
      home: "Home",
      explore: "Explore",
      trending: "Trending",
      saved: "Saved",
      categories: "Categories",
      sidebar_tagline: "Promptly — built for prompt creators",
      notifications: "Notifications",
      profile: "Profile",
      for_you: "For You",
      latest: "Latest",
      following: "Following",
      trending_now: "🔥 Trending now",
      popular_categories: "Popular categories",
      creators_to_follow: "Creators to follow",
      just_added: "✨ Just added",
      posts: "posts",
      no_categories_yet: "No categories with posts yet.",
      no_creators_yet: "No creators yet.",
      results_for: "Results for \u201c{query}\u201d",
      search_title: "Search",
      search_hint: "Type something in the search bar above — titles, prompts, tags, AI models or creators.",
      welcome_back: "Welcome back",
      login_tagline: "Log in to share prompts, save ideas and follow creators.",
      username_or_email: "Username or email",
      password: "Password",
      no_account: "No account?",
      create_account: "Create your account",
      signup_tagline: "Join the community of prompt creators.",
      username: "Username",
      email: "Email",
      password_min: "Password",
      password_hint: "(min 8 chars)",
      have_account: "Already have an account?",
      mark_all_read: "Mark all as read",
      no_notifications: "No notifications yet.",
      liked_your_post: "liked your post",
      saved_your_post: "saved your post",
      commented_on_your_post: "commented on your post",
      started_following_you: "started following you",
      followers: "followers",
      level: "Level",
      follow: "Follow",
      following_btn: "Following",
      offline_title: "You're offline",
      offline_body: "Promptly isn't available right now, but your cached pages still work. Check your connection and try again.",
      try_again: "Try again",
      views: "views",
      prompt: "PROMPT",
      copy: "Copy",
      model: "Model:",
      copies: "copies",
      comments: "comments",
      comments_title: "Comments",
      comment_placeholder: "Share your thoughts…",
      comment_btn: "Comment",
      login_to_join: "Log in to join the conversation.",
      share_a_prompt: "Share a prompt",
      title: "Title",
      type: "Type",
      prompt_type: "Prompt",
      image: "Image",
      video: "Video",
      audio: "Audio",
      category: "Category",
      choose_category: "Choose a category…",
      ai_model: "AI model",
      optional: "(optional)",
      the_prompt: "The prompt",
      description: "Description",
      title_placeholder: "e.g. Cinematic portrait generator",
      ai_model_placeholder: "e.g. GPT-5, Midjourney, Sora",
      prompt_placeholder: "Paste the prompt you used…",
      description_placeholder: "What makes this prompt special?",
      publish: "Publish",
      nothing_here: "Nothing here yet.",
      share_first_prompt: "Share your first prompt",
      post_count: "{n} posts",
      level_n: "Level {n}",
      // JS-side dynamic strings
      saved_toast: "Saved 🔖",
      removed_from_saved: "Removed from saved",
      login_to_do_that: "Log in to do that",
      something_wrong: "Something went wrong",
      follow_error: "Could not update follow",
      copied: "Copied!",
      copy_toast: "Prompt copied to clipboard",
      comment_posted: "Comment posted",
      comment_error: "Could not post comment",
      published_toast: "Published! 🎉",
      publish_error: "Could not publish. Check your input and try again.",
      caught_up_toast: "All caught up ✨",
      delete: "Delete",
      verified: "Verified",
      // date formatting
      date_locale: "en-US",
    },
    fa: {
      search_placeholder: "جستجوی پرامپت‌ها…",
      toggle_theme: "تغییر حالت شب و روز",
      switch_language: "تغییر زبان",
      lang_switch_label: "EN",
      create: "ساختن",
      login: "ورود",
      signup: "ثبت‌نام",
      home: "خانه",
      explore: "کاوش",
      trending: "پرطرفدار",
      saved: "ذخیره‌شده",
      categories: "دسته‌بندی‌ها",
      sidebar_tagline: "پرامپت‌لی — ساخته‌شده برای سازندگان پرامپت",
      notifications: "اعلان‌ها",
      profile: "پروفایل",
      for_you: "مخصوص شما",
      latest: "جدیدترین",
      following: "دنبال‌شده‌ها",
      trending_now: "🔥 پرطرفدارترین‌ها",
      popular_categories: "دسته‌بندی‌های محبوب",
      creators_to_follow: "سازندگان پیشنهادی",
      just_added: "✨ تازه اضافه‌شده",
      posts: "پست",
      no_categories_yet: "هنوز دسته‌بندی‌ای با پست وجود ندارد.",
      no_creators_yet: "هنوز سازنده‌ای وجود ندارد.",
      results_for: "نتایج برای «{query}»",
      search_title: "جستجو",
      search_hint: "چیزی در نوار جستجوی بالا بنویسید — عنوان‌ها، پرامپت‌ها، برچسب‌ها، مدل‌های هوش مصنوعی یا سازندگان.",
      welcome_back: "خوش آمدید",
      login_tagline: "برای اشتراک پرامپت، ذخیره ایده‌ها و دنبال کردن سازندگان وارد شوید.",
      username_or_email: "نام کاربری یا ایمیل",
      password: "گذرواژه",
      no_account: "حساب ندارید؟",
      create_account: "حساب خود را بسازید",
      signup_tagline: "به جمع سازندگان پرامپت بپیوندید.",
      username: "نام کاربری",
      email: "ایمیل",
      password_min: "گذرواژه",
      password_hint: "(حداقل ۸ کاراکتر)",
      have_account: "قبلاً حساب ساخته‌اید؟",
      mark_all_read: "علامت‌گذاری همه به‌عنوان خوانده‌شده",
      no_notifications: "هنوز اعلانی وجود ندارد.",
      liked_your_post: "پست شما را پسندید",
      saved_your_post: "پست شما را ذخیره کرد",
      commented_on_your_post: "روی پست شما نظر گذاشت",
      started_following_you: "شما را دنبال کرد",
      followers: "دنبال‌کننده",
      level: "سطح",
      follow: "دنبال کردن",
      following_btn: "دنبال می‌کنید",
      offline_title: "شما آفلاین هستید",
      offline_body: "پرامپت‌لی در دسترس نیست، اما صفحه‌های ذخیره‌شده کار می‌کنند. اتصال خود را بررسی و دوباره تلاش کنید.",
      try_again: "تلاش دوباره",
      views: "بازدید",
      prompt: "پرامپت",
      copy: "کپی",
      model: "مدل:",
      copies: "کپی",
      comments: "نظر",
      comments_title: "نظرها",
      comment_placeholder: "نظر خود را بنویسید…",
      comment_btn: "ثبت نظر",
      login_to_join: "برای گفتگو وارد شوید.",
      share_a_prompt: "اشتراک یک پرامپت",
      title: "عنوان",
      type: "نوع",
      prompt_type: "پرامپت",
      image: "تصویر",
      video: "ویدیو",
      audio: "صدا",
      category: "دسته‌بندی",
      choose_category: "یک دسته‌بندی انتخاب کنید…",
      ai_model: "مدل هوش مصنوعی",
      optional: "(اختیاری)",
      the_prompt: "متن پرامپت",
      description: "توضیحات",
      title_placeholder: "مثلاً: تولید پرتره سینمایی",
      ai_model_placeholder: "مثلاً: GPT-5، Midjourney، Sora",
      prompt_placeholder: "پرامپتی که استفاده کردید را بچسبانید…",
      description_placeholder: "چه چیز این پرامپت را خاص می‌کند؟",
      publish: "انتشار",
      nothing_here: "هنوز چیزی اینجا نیست.",
      share_first_prompt: "اولین پرامپت خود را به اشتراک بگذارید",
      post_count: "{n} پست",
      level_n: "سطح {n}",
      // JS-side dynamic strings
      saved_toast: "ذخیره شد 🔖",
      removed_from_saved: "از ذخیره‌شده‌ها حذف شد",
      login_to_do_that: "برای این کار وارد شوید",
      something_wrong: "مشکلی پیش آمد",
      follow_error: "دنبال کردن به‌روزرسانی نشد",
      copied: "کپی شد!",
      copy_toast: "پرامپت در کلیپ‌بورد کپی شد",
      comment_posted: "نظر ثبت شد",
      comment_error: "ثبت نظر ممکن نشد",
      published_toast: "منتشر شد! 🎉",
      publish_error: "انتشار ممکن نشد. ورودی خود را بررسی کنید.",
      caught_up_toast: "همه خوانده شد ✨",
      delete: "حذف",
      verified: "تأییدشده",
      // date formatting
      date_locale: "fa-IR",
    },
  };

  var LANG_KEY = "promptly-lang";

  function readLang() {
    // Server renders pages from the cookie; trust it first, then localStorage.
    if (global.PROMPTLY_LANG === "fa" || global.PROMPTLY_LANG === "en") return global.PROMPTLY_LANG;
    try {
      var stored = localStorage.getItem(LANG_KEY);
      if (stored === "en" || stored === "fa") return stored;
      if (navigator.language && navigator.language.indexOf("fa") === 0) return "fa";
    } catch (e) {}
    return "en";
  }

  function persist(lang) {
    try { localStorage.setItem(LANG_KEY, lang); } catch (e) {}
    // Keep the server cookie in sync so the next page renders in this language.
    document.cookie =
      LANG_KEY + "=" + lang + "; path=/; max-age=31536000; samesite=Lax";
  }

  function t(key, params) {
    var lang = currentLang;
    var str = (STRINGS[lang] && STRINGS[lang][key]) || STRINGS.en[key] || key;
    if (params) {
      Object.keys(params).forEach(function (k) {
        str = str.replace(new RegExp("\\{" + k + "\\}", "g"), params[k]);
      });
    }
    return str;
  }

  function applyStatic() {
    var html = document.documentElement;
    var lang = currentLang;
    html.setAttribute("lang", lang);
    html.setAttribute("dir", lang === "fa" ? "rtl" : "ltr");

    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var key = el.getAttribute("data-i18n");
      var text = t(key);
      if (el.textContent !== text) el.textContent = text;
    });

    var searchInput = document.querySelector(".search input");
    if (searchInput) searchInput.placeholder = t("search_placeholder");

    document.querySelectorAll("#theme-toggle").forEach(function (btn) {
      btn.setAttribute("aria-label", t("toggle_theme"));
      btn.setAttribute("title", t("toggle_theme"));
    });

    document.querySelectorAll("#lang-btn, #lang-btn-footer").forEach(function (btn) {
      var span = btn.querySelector("span");
      if (span) span.textContent = t("lang_switch_label");
      btn.setAttribute("aria-label", t("switch_language"));
    });
  }

  function switchLanguage(lang) {
    currentLang = (lang === "fa" || lang === "en") ? lang : (currentLang === "fa" ? "en" : "fa");
    persist(currentLang);
    applyStatic();
    if (typeof global.promptlyApplyPageI18n === "function") global.promptlyApplyPageI18n();
    window.dispatchEvent(new CustomEvent("promptly:langchange", { detail: { lang: currentLang } }));
  }

  var currentLang = "en";

  var api = {
    init: function () {
      currentLang = readLang();
      applyStatic();
    },
    getLang: function () { return currentLang; },
    isRTL: function () { return currentLang === "fa"; },
    switch: switchLanguage,
    toggle: function () { switchLanguage(currentLang === "fa" ? "en" : "fa"); },
    t: t,
    dateLocale: function () {
      return (STRINGS[currentLang] && STRINGS[currentLang].date_locale) || "en-US";
    },
  };

  global.PromptlyI18n = api;

  document.addEventListener("DOMContentLoaded", function () {
    api.init();
    document.querySelectorAll("#lang-btn, #lang-btn-footer").forEach(function (btn) {
      btn.addEventListener("click", function () { api.toggle(); });
    });
  });
})(window);
