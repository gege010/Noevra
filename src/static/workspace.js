/* Durable non-secret preferences, report wayfinding, and tab-scoped OAuth. */
(function (root) {
  const defaults = {
    theme: "light",
    reading: "standard",
    collapsed: false,
    motion: false,
    provider: "groq",
    depth: "standard",
    language: "en",
    citation: "ieee",
    sources: "20",
  };
  let preferences = { ...defaults },
    headings = [],
    pendingSection = null,
    navigationFrame = 0,
    sectionTimer;
  function save() {
    try {
      localStorage.setItem("scholar_preferences", JSON.stringify(preferences));
    } catch {
      notify(
        "Browser storage is unavailable. Preferences apply only until reload.",
      );
    }
  }
  function setCollapsed(value) {
    preferences.collapsed = Boolean(value);
    document.documentElement.classList.toggle(
      "sidebar-collapsed",
      preferences.collapsed,
    );
    $("compactSidebar").checked = preferences.collapsed;
    $("sidebarToggle").setAttribute(
      "aria-expanded",
      String(!preferences.collapsed),
    );
    $("sidebarToggle").setAttribute(
      "aria-label",
      preferences.collapsed ? "Expand sidebar" : "Minimize sidebar",
    );
    $("sidebarToggle").title = preferences.collapsed
      ? "Expand sidebar"
      : "Minimize sidebar";
    save();
  }
  function applyAppearance() {
    const theme =
      preferences.theme === "system"
        ? matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light"
        : preferences.theme;
    document.documentElement.dataset.theme = theme;
    document.documentElement.dataset.readingSize = preferences.reading;
    document.documentElement.dataset.reduceMotion = String(preferences.motion);
    $("appearanceTheme").value = preferences.theme;
    $("readingSize").value = preferences.reading;
    $("reduceMotion").checked = preferences.motion;
    updateThemeButton();
    root.ScholarControls?.sync();
  }
  function setTheme(theme) {
    if (!["light", "dark", "system"].includes(theme)) return;
    preferences.theme = theme;
    applyAppearance();
    save();
  }
  function applyDefaults() {
    for (const [id, value] of Object.entries({
      depthSelect: preferences.depth,
      languageSelect: preferences.language,
      citationSelect: preferences.citation,
      sourceLimit: preferences.sources,
    }))
      $(id).value = value;
    if (state.providers[preferences.provider]) {
      state.provider = preferences.provider;
      $("providerSelect").value = state.provider;
      populateConnection(state.provider);
    }
    root.ScholarControls?.sync();
  }
  function settingsTab(name) {
    document.querySelectorAll("[data-settings-tab]").forEach((button) => {
      const active = button.dataset.settingsTab === name;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    document
      .querySelectorAll("[data-settings-panel]")
      .forEach(
        (panel) => (panel.hidden = panel.dataset.settingsPanel !== name),
      );
    root.ScholarControls?.close();
  }
  function openSettings(tab) {
    if (tab) settingsTab(tab);
    for (const [id, key] of Object.entries({
      defaultProvider: "provider",
      defaultDepth: "depth",
      defaultLanguage: "language",
      defaultCitation: "citation",
      defaultSources: "sources",
    }))
      $(id).value = preferences[key];
    applyAppearance();
    updateOAuthStatus();
    openDialog("settingsDialog");
    root.ScholarControls?.sync();
  }
  function activeSection(id) {
    $("reportToc")
      .querySelectorAll("a")
      .forEach((link) => {
        const active = link.hash === "#" + id;
        link.classList.toggle("active", active);
        if (active) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
  }
  function updateReportNavigation() {
    if (
      state.view !== "report" ||
      $("panelDocument").hidden ||
      !headings.length
    )
      return;
    if (pendingSection) {
      activeSection(pendingSection);
      return;
    }
    let active = headings[0].id;
    const boundary = Math.max(180, Math.min(innerHeight * 0.28, 240));
    for (const heading of headings) {
      if (heading.getBoundingClientRect().top <= boundary) active = heading.id;
      else break;
    }
    if (
      scrollY > 0 &&
      scrollY + innerHeight >= document.documentElement.scrollHeight - 5
    )
      active = headings.at(-1).id;
    activeSection(active);
  }
  function setupReportNavigation() {
    headings = [...$("reportArticle").querySelectorAll("h2[id]")];
    pendingSection = null;
    if (headings.length) activeSection(headings[0].id);
  }
  function requestNavigationUpdate() {
    if (navigationFrame) return;
    navigationFrame = requestAnimationFrame(() => {
      navigationFrame = 0;
      updateReportNavigation();
    });
  }
  function releaseSection() {
    pendingSection = null;
    clearTimeout(sectionTimer);
    requestNavigationUpdate();
  }
  function updateOAuthStatus() {
    root.NoevraProviders?.renderConnections();
  }
  async function handleOAuthCallback() {
    await root.NoevraProviders?.handleCallback();
  }
  function init() {
    try {
      const saved = JSON.parse(
        localStorage.getItem("scholar_preferences") || "{}",
      );
      for (const key of [
        "theme",
        "reading",
        "provider",
        "depth",
        "language",
        "citation",
        "sources",
      ])
        if (typeof saved[key] === "string") preferences[key] = saved[key];
      for (const key of ["collapsed", "motion"])
        if (typeof saved[key] === "boolean") preferences[key] = saved[key];
      if (!["light", "dark", "system"].includes(preferences.theme))
        preferences.theme = "light";
      if (!["standard", "large", "extra"].includes(preferences.reading))
        preferences.reading = "standard";
      if (!["quick", "standard", "deep"].includes(preferences.depth))
        preferences.depth = "standard";
      if (!["en", "id"].includes(preferences.language))
        preferences.language = "en";
      if (!["ieee", "apa", "nature", "harvard"].includes(preferences.citation))
        preferences.citation = "ieee";
      if (!["10", "20", "30", "50"].includes(preferences.sources))
        preferences.sources = "20";
    } catch {}
    applyAppearance();
    setCollapsed(preferences.collapsed);
    applyDefaults();
    $("sidebarToggle").addEventListener("click", () =>
      setCollapsed(!preferences.collapsed),
    );
    $("compactSidebar").addEventListener("change", () =>
      setCollapsed($("compactSidebar").checked),
    );
    $("appearanceTheme").addEventListener("change", () =>
      setTheme($("appearanceTheme").value),
    );
    $("readingSize").addEventListener("change", () => {
      preferences.reading = $("readingSize").value;
      applyAppearance();
      save();
      requestNavigationUpdate();
    });
    $("reduceMotion").addEventListener("change", () => {
      preferences.motion = $("reduceMotion").checked;
      applyAppearance();
      save();
    });
    for (const [id, key] of Object.entries({
      defaultProvider: "provider",
      defaultDepth: "depth",
      defaultLanguage: "language",
      defaultCitation: "citation",
      defaultSources: "sources",
    }))
      $(id).addEventListener("change", () => {
        preferences[key] = $(id).value;
        save();
      });
    document
      .querySelectorAll("[data-settings-tab]")
      .forEach((button) =>
        button.addEventListener("click", () =>
          settingsTab(button.dataset.settingsTab),
        ),
      );
    $("reportToc").addEventListener("click", (event) => {
      const link = event.target.closest("a");
      if (!link) return;
      const target = document.getElementById(link.hash.slice(1));
      if (!target) return;
      event.preventDefault();
      pendingSection = target.id;
      activeSection(target.id);
      history.replaceState(
        null,
        "",
        location.pathname + location.search + link.hash,
      );
      target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
      target.scrollIntoView({
        block: "start",
        behavior:
          preferences.motion ||
          matchMedia("(prefers-reduced-motion: reduce)").matches
            ? "instant"
            : "smooth",
      });
      clearTimeout(sectionTimer);
      sectionTimer = setTimeout(releaseSection, 1000);
    });
    addEventListener("scroll", requestNavigationUpdate, { passive: true });
    addEventListener("scrollend", releaseSection);
    addEventListener("wheel", releaseSection, { passive: true });
    addEventListener("touchstart", releaseSection, { passive: true });
    addEventListener("resize", requestNavigationUpdate);
    matchMedia("(prefers-color-scheme: dark)").addEventListener(
      "change",
      () => {
        if (preferences.theme === "system") applyAppearance();
      },
    );
    updateOAuthStatus();
  }
  root.ScholarWorkspace = {
    init,
    openSettings,
    setTheme,
    applyDefaults,
    updateOAuthStatus,
    setupReportNavigation,
    updateReportNavigation,
    handleOAuthCallback,
    get preferences() {
      return preferences;
    },
  };
})(window);
